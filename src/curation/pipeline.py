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

@dataclass
class PipelineRun:
    config_hash: str
    stages: list[StageResult] = field(default_factory=list)
    final: list[Record] = field(default_factory=list)


def run_pipeline(cfg: PipelineConfig) -> PipelineRun:
    run = PipelineRun(config_hash=cfg.config_hash())

    first = ingest(cfg.input_paths)
    run.stages.append(first)
    records = first.kept

    steps: list[Callable[[list[Record]], StageResult]] = [
        lambda recs: normalize(recs, cfg.normalize),
        lambda recs: quality_filter(recs, cfg.quality),
        lambda recs: safety_filter(recs, cfg.safety),
        lambda recs: language_filter(recs, cfg.language, cfg.seed),
        exact_dedup,
        lambda recs: near_dedup(recs, cfg.dedup, cfg.seed),
    ]

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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Dataset curation pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    run = run_pipeline(cfg)
    print_funnel(run)


if __name__ == "__main__":
    main()