from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from curation.config import ContaminationConfig
from curation.dedup import _tokens
from curation.result import Removed, StageResult
from curation.schema import Record

STAGE_CONTAM = "contamination"


def _ngrams(tokens: list[str], n: int) -> Iterable[str]:
    return (" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def load_benchmark_index(cfg: ContaminationConfig) -> dict[str, str]:
    """Map every benchmark n-gram to the name of the benchmark it came from."""
    index: dict[str, str] = {}
    for name in cfg.benchmarks:
        path = Path(cfg.benchmark_dir) / f"{name}.jsonl"
        if not path.exists():
            raise FileNotFoundError(
                f"benchmark file not found: {path} (run the matching scripts/fetch_*.py)"
            )
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                tokens = _tokens(json.loads(line)["text"])
                for gram in _ngrams(tokens, cfg.ngram_size):
                    index.setdefault(gram, name)
    return index


def contamination_filter(
    records: Iterable[Record], index: dict[str, str], ngram_size: int
) -> StageResult:
    result = StageResult(stage=STAGE_CONTAM)
    result.stats["benchmark_ngrams"] = len(index)

    for rec in records:
        tokens = _tokens(rec.content())
        if len(tokens) < ngram_size:
            result.stats["too_short_to_check"] = result.stats.get("too_short_to_check", 0) + 1
            result.kept.append(rec)
            continue

        hit = next((g for g in _ngrams(tokens, ngram_size) if g in index), None)
        if hit is None:
            result.kept.append(rec)
            continue

        bench = index[hit]
        key = f"hits_{bench}"
        result.stats[key] = result.stats.get(key, 0) + 1
        result.removed.append(
            Removed(rec.id, STAGE_CONTAM, "benchmark_contamination", f"{bench}: {hit[:80]}")
        )
    return result