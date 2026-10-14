from __future__ import annotations

import statistics
from collections import Counter
from typing import Iterable

from curation.dedup import _tokens
from curation.schema import Record


def _percentile(sorted_vals: list[int], q: float) -> int:
    if not sorted_vals:
        return 0
    return sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))]


def compute_stats(records: Iterable[Record]) -> dict:
    recs = list(records)
    lengths = sorted(len(r.content()) for r in recs)

    unigrams: set[str] = set()
    bigrams: set[tuple[str, str]] = set()
    n_uni = 0
    n_bi = 0
    for r in recs:
        toks = _tokens(r.content())
        n_uni += len(toks)
        unigrams.update(toks)
        pairs = list(zip(toks, toks[1:]))
        n_bi += len(pairs)
        bigrams.update(pairs)

    return {
        "n_records": len(recs),
        "total_chars": sum(lengths),
        "mean_chars": round(statistics.mean(lengths), 1) if lengths else 0,
        "median_chars": statistics.median(lengths) if lengths else 0,
        "p95_chars": _percentile(lengths, 0.95),
        "n_tokens": n_uni,
        "vocab_size": len(unigrams),
        "distinct_1": round(len(unigrams) / n_uni, 4) if n_uni else 0,
        "distinct_2": round(len(bigrams) / n_bi, 4) if n_bi else 0,
        "kinds": dict(Counter(r.kind for r in recs)),
        "sources": dict(Counter(r.source for r in recs)),
        "languages": dict(Counter(r.meta["lang"] for r in recs if "lang" in r.meta)),
    }