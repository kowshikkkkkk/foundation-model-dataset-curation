from __future__ import annotations

import hashlib
from typing import Iterable

from curation.result import Removed, StageResult
from curation.schema import Record

import unicodedata

from datasketch import MinHash, MinHashLSH

from curation.config import DedupConfig

STAGE_EXACT = "exact_dedup"


def content_hash(rec: Record) -> str:
    h = hashlib.sha256()
    h.update(rec.kind.encode("utf-8"))
    h.update(b"\x00")  # separator so kind and content can't blur together
    h.update(rec.content().encode("utf-8"))
    return h.hexdigest()


def exact_dedup(records: Iterable[Record]) -> StageResult:
    result = StageResult(stage=STAGE_EXACT)
    seen: dict[str, str] = {}  # content hash -> id of first record

    for rec in records:
        key = content_hash(rec)
        first_id = seen.get(key)
        if first_id is None:
            seen[key] = rec.id
            result.kept.append(rec)
        else:
            result.removed.append(
                Removed(rec.id, STAGE_EXACT, "exact_duplicate", f"duplicate of {first_id}")
            )
    return result

STAGE_NEAR = "near_dedup"


def _tokens(text: str) -> list[str]:
    # Replace punctuation with spaces; keep combining marks (needed for Indic scripts).
    cleaned = "".join(
        " " if unicodedata.category(ch).startswith("P") else ch
        for ch in text.lower()
    )
    return cleaned.split()


def shingles(text: str, size: int) -> set[str]:
    toks = _tokens(text)
    if not toks:
        return set()
    if len(toks) < size:
        return {" ".join(toks)}  # short text: one shingle
    return {" ".join(toks[i:i + size]) for i in range(len(toks) - size + 1)}


def _minhash(shingle_set: set[str], num_perm: int, seed: int) -> MinHash:
    m = MinHash(num_perm=num_perm, seed=seed)
    for s in shingle_set:
        m.update(s.encode("utf-8"))
    return m


def near_dedup(records: Iterable[Record], cfg: DedupConfig, seed: int) -> StageResult:
    result = StageResult(stage=STAGE_NEAR)
    lsh = MinHashLSH(threshold=cfg.lsh_threshold, num_perm=cfg.num_perm)
    indexed: dict[str, tuple[Record, MinHash]] = {}

    for i, rec in enumerate(records):
        sh = shingles(rec.content(), cfg.shingle_size)
        if not sh:
            result.kept.append(rec)
            continue

        m = _minhash(sh, cfg.num_perm, seed)
        candidates = lsh.query(m)

        if candidates:
            best = max(sorted(candidates, key=int), key=lambda k: m.jaccard(indexed[k][1]))
            orig, orig_m = indexed[best]
            sim = m.jaccard(orig_m)
            result.removed.append(
                Removed(rec.id, STAGE_NEAR, "near_duplicate", f"~{sim:.2f} similar to {orig.id}")
            )
            continue

        key = str(i)
        lsh.insert(key, m)
        indexed[key] = (rec, m)
        result.kept.append(rec)

    return result