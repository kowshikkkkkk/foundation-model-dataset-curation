from __future__ import annotations

import hashlib
from typing import Iterable

from curation.result import Removed, StageResult
from curation.schema import Record

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