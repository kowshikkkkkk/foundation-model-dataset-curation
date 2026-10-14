from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from curation.result import Removed, StageResult
from curation.schema import Record

STAGE = "ingest"
_KNOWN_KEYS = {"id", "text", "instruction", "response", "output"}


def _fallback_id(source: str, lineno: int) -> str:
    return hashlib.sha1(f"{source}:{lineno}".encode("utf-8")).hexdigest()[:16]


def _detect_kind(row: dict) -> str | None:
    if "text" in row:
        return "document"
    if "instruction" in row:
        return "instruction"
    return None


def _ingest_file(path: Path, result: StageResult) -> None:
    source = path.as_posix()
    with open(path, "r", encoding="utf-8-sig") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue  # blank lines are not records

            fallback = _fallback_id(source, lineno)

            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                result.removed.append(Removed(fallback, STAGE, "json_decode_error", str(e)))
                continue

            if not isinstance(row, dict):
                result.removed.append(Removed(fallback, STAGE, "not_an_object"))
                continue

            kind = _detect_kind(row)
            rid = str(row["id"]) if "id" in row else fallback
            if kind is None:
                result.removed.append(Removed(rid, STAGE, "unrecognized_shape"))
                continue

            meta = {k: v for k, v in row.items() if k not in _KNOWN_KEYS}
            meta["line"] = lineno

            try:
                record = Record(
                    id=rid,
                    kind=kind,
                    source=source,
                    text=row.get("text"),
                    instruction=row.get("instruction"),
                    response=row.get("response", row.get("output")),
                    meta=meta,
                )
            except ValidationError as e:
                msg = e.errors()[0]["msg"]
                result.removed.append(Removed(rid, STAGE, "schema_invalid", msg))
                continue

            result.kept.append(record)


def ingest(paths: Iterable[str | Path]) -> StageResult:
    result = StageResult(stage=STAGE)
    for p in paths:
        _ingest_file(Path(p), result)
    return result