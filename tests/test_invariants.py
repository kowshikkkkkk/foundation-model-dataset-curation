from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from curation.config import ContaminationConfig, PipelineConfig
from curation.export import export_dataset
from curation.pipeline import run_pipeline

ROWS = [
    {"text": "The committee met on Tuesday to discuss the new budget proposal and its effect on local schools."},
    {"text": "The committee met on Tuesday to discuss the new budget proposal and its effect on local schools."},
    {"text": "Rainfall in the coastal region was above average this season, and farmers reported strong yields of rice and sugarcane across most districts."},
    {"instruction": "What is the capital of France?", "response": "The capital of France is Paris."},
    {"instruction": "Say hi", "response": ""},
    {"text": "!!!! ???? #### $$$$ %%%% ^^^^ !!!! ???? ####"},
]
BAD_LINE = "this line is not json"


@pytest.fixture
def input_file(tmp_path: Path):
    lines = [json.dumps(r, ensure_ascii=False) for r in ROWS] + [BAD_LINE]
    path = tmp_path / "input.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, len(lines)


def make_cfg(input_path: Path, out_dir: Path) -> PipelineConfig:
    return PipelineConfig(
        input_paths=(str(input_path),),
        output_dir=str(out_dir),
        contamination=ContaminationConfig(benchmarks=()),
    )


def test_every_line_accounted_for_exactly_once(input_file, tmp_path):
    path, n_lines = input_file
    run = run_pipeline(make_cfg(path, tmp_path / "out"))

    removed_ids = [r.record_id for s in run.stages for r in s.removed]
    final_ids = [rec.id for rec in run.final]

    assert len(removed_ids) + len(final_ids) == n_lines
    assert len(set(removed_ids)) == len(removed_ids)
    assert not set(removed_ids) & set(final_ids)


def test_stages_chain_and_reasons_present(input_file, tmp_path):
    path, _ = input_file
    run = run_pipeline(make_cfg(path, tmp_path / "out"))

    for prev, cur in zip(run.stages, run.stages[1:]):
        assert cur.n_in == prev.n_out
    assert all(r.reason for s in run.stages for r in s.removed)


def test_deterministic_export(input_file, tmp_path):
    path, _ = input_file
    results = []
    for name in ("a", "b"):
        cfg = make_cfg(path, tmp_path / name)
        out = export_dataset(run_pipeline(cfg).final, cfg.output_dir)
        digest = hashlib.sha256(Path(out["jsonl"]).read_bytes()).hexdigest()
        results.append((cfg.config_hash(), digest))

    assert results[0] == results[1]