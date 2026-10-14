from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.parquet as pq

from curation.schema import Record

_SCHEMA = pa.schema([
    ("id", pa.string()),
    ("kind", pa.string()),
    ("source", pa.string()),
    ("text", pa.string()),
    ("instruction", pa.string()),
    ("response", pa.string()),
    ("lang", pa.string()),
    ("lang_conf", pa.float64()),
    ("meta_json", pa.string()),  # full meta, lossless
])


def _row(rec: Record) -> dict:
    return {
        "id": rec.id,
        "kind": rec.kind,
        "source": rec.source,
        "text": rec.text,
        "instruction": rec.instruction,
        "response": rec.response,
        "lang": rec.meta.get("lang"),
        "lang_conf": rec.meta.get("lang_conf"),
        "meta_json": json.dumps(rec.meta, sort_keys=True, ensure_ascii=False),
    }


def export_dataset(records: Iterable[Record], out_dir: str | Path) -> dict:
    recs = list(records)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    jsonl_path = out / "curated.jsonl"
    parquet_path = out / "curated.parquet"

    with open(jsonl_path, "w", encoding="utf-8", newline="\n") as f:
        for rec in recs:
            line = json.dumps(rec.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            f.write(line + "\n")

    table = pa.Table.from_pylist([_row(r) for r in recs], schema=_SCHEMA)
    pq.write_table(table, parquet_path, compression="zstd")

    return {"jsonl": jsonl_path, "parquet": parquet_path, "n_records": len(recs)}