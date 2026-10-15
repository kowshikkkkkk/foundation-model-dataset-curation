from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from curation.config import PipelineConfig
from curation.result import StageResult

_PACKAGES = ("pydantic", "pyyaml", "datasketch", "langdetect", "pyarrow")


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_info(path: str | Path) -> dict:
    p = Path(path)
    return {"path": p.as_posix(), "sha256": file_sha256(p), "bytes": p.stat().st_size}


def dataset_version(
    input_infos: list[dict], config_hash: str, benchmark_infos: list[dict] = ()
) -> str:
    # Order is kept on purpose: input order can change which duplicate survives.
    body = {"inputs": [i["sha256"] for i in input_infos], "config": config_hash}
    if benchmark_infos:
        body["benchmarks"] = [b["sha256"] for b in benchmark_infos]
    payload = json.dumps(body, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _code_info() -> dict:
    status = _git("status", "--porcelain")
    versions = {}
    for pkg in _PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = None
    return {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": None if status is None else bool(status),
        "python": platform.python_version(),
        "packages": versions,
    }


def build_manifest(cfg: PipelineConfig, stages: list[StageResult], outputs: dict) -> dict:
    inputs = [_file_info(p) for p in cfg.input_paths]
    config_hash = cfg.config_hash()
    benchmarks = [
        _file_info(Path(cfg.contamination.benchmark_dir) / f"{name}.jsonl")
        for name in cfg.contamination.benchmarks
    ]
    return {
        "dataset_version": dataset_version(inputs, config_hash, benchmarks),
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config_hash": config_hash,
        "config": cfg.model_dump(mode="json"),
        "inputs": inputs,
        "benchmarks": benchmarks,
        "outputs": {
            "jsonl": _file_info(outputs["jsonl"]),
            "parquet": _file_info(outputs["parquet"]),
        },
        "n_records": outputs["n_records"],
        "stages": [
            {
                "stage": s.stage,
                "n_in": s.n_in,
                "n_out": s.n_out,
                "removed": s.reason_counts(),
                "stats": s.stats,
            }
            for s in stages
        ],
        "code": _code_info(),
    }


def write_manifest(
    cfg: PipelineConfig, stages: list[StageResult], outputs: dict, out_dir: str | Path
) -> dict:
    manifest = build_manifest(cfg, stages, outputs)
    path = Path(out_dir) / "manifest.json"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    return manifest