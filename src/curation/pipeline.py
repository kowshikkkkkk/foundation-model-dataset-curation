from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Callable

from curation.config import PipelineConfig, load_config
from curation.dedup import exact_dedup, near_dedup
from curation.filters import quality_filter
from curation.ingest import ingest
from curation.normalize import normalize
from curation.result import StageResult
from curation.safety import safety_filter
from curation.schema import Record
from curation.language import language_filter
from curation.stats import compute_stats
from curation.export import export_dataset
from curation.provenance import write_manifest
from curation.report import write_report
from curation.contamination import contamination_filter, load_benchmark_index


@dataclass
class PipelineRun:
    config_hash: str
    stages: list[StageResult] = field(default_factory=list)
    final: list[Record] = field(default_factory=list)
    before: dict = field(default_factory=dict)
    after: dict = field(default_factory=dict)


def run_pipeline(cfg: PipelineConfig) -> PipelineRun:
    run = PipelineRun(config_hash=cfg.config_hash())

    first = ingest(cfg.input_paths)
    run.stages.append(first)
    records = first.kept
    run.before = compute_stats(records)

    steps: list[Callable[[list[Record]], StageResult]] = [
        lambda recs: normalize(recs, cfg.normalize),
        lambda recs: quality_filter(recs, cfg.quality),
        lambda recs: safety_filter(recs, cfg.safety),
        lambda recs: language_filter(recs, cfg.language, cfg.seed),
        exact_dedup,
        lambda recs: near_dedup(recs, cfg.dedup, cfg.seed),
    ]
    if cfg.contamination.benchmarks:
        index = load_benchmark_index(cfg.contamination)
        n = cfg.contamination.ngram_size
        steps.insert(4, lambda recs: contamination_filter(recs, index, n))

    for step in steps:
        n_before = len(records)
        result = step(records)
        if result.n_in != n_before:
            raise RuntimeError(
                f"stage '{result.stage}' lost records: got {n_before}, "
                f"accounted for {result.n_in}"
            )
        run.stages.append(result)
        records = result.kept

    run.after = compute_stats(records)
    run.final = records

    return run


def print_funnel(run: PipelineRun) -> None:
    print(f"config_hash: {run.config_hash[:12]}")
    print(f"{'stage':<14}{'in':>7}{'out':>7}{'removed':>9}  reasons")
    for s in run.stages:
        reasons = s.reason_counts() or ""
        print(f"{s.stage:<14}{s.n_in:>7}{s.n_out:>7}{len(s.removed):>9}  {reasons}")
        if s.stats:
            print(f"{'':<14}stats: {s.stats}")
    print(f"final records: {len(run.final)}")
    print()
    print(f"{'metric':<16}{'before':>10}{'after':>10}")
    for key in ("n_records", "mean_chars", "vocab_size", "distinct_1", "distinct_2"):
        print(f"{key:<16}{run.before[key]:>10}{run.after[key]:>10}")
    print("languages (after):", run.after["languages"])

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Dataset curation pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    run = run_pipeline(cfg)
    print_funnel(run)

    out = export_dataset(run.final, cfg.output_dir)
    print(f"exported {out['n_records']} records to {out['jsonl']} and {out['parquet']}")
    manifest = write_manifest(cfg, run.stages, out, cfg.output_dir)
    print(f"dataset_version: {manifest['dataset_version']}")
    report_path = write_report(run.stages, run.before, run.after, manifest, cfg.output_dir)
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()