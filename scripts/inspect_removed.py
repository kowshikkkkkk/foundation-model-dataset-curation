from __future__ import annotations

import argparse
import json
import random
import sys

from curation.config import load_config
from curation.pipeline import run_pipeline
from curation.safety import _PATTERNS


def load_raw(paths) -> dict[str, dict]:
    raw: dict[str, dict] = {}
    for p in paths:
        with open(p, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and "id" in row:
                    raw[str(row["id"])] = row
    return raw


def oneline(value, limit: int) -> str:
    s = str(value).replace("\n", "\\n")
    return s if len(s) <= limit else s[:limit] + "..."


def raw_content(row: dict) -> str:
    keys = ("text", "instruction", "response", "output")
    return "\n".join(str(row[k]) for k in keys if k in row)


def show_row(row: dict | None, limit: int) -> None:
    if row is None:
        print("    (raw row not found)")
        return
    for key in ("text", "instruction", "response", "output"):
        if key in row:
            print(f"    {key}: {oneline(row[key], limit)}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("-n", type=int, default=5, help="samples per group")
    ap.add_argument("--chars", type=int, default=300)
    ap.add_argument("--reason", nargs="*", default=None, help="only these reason codes")
    ap.add_argument("--redactions", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    raw = load_raw(cfg.input_paths)
    run = run_pipeline(cfg)
    rng = random.Random(0)

    groups: dict[tuple[str, str], list] = {}
    for stage in run.stages:
        for r in stage.removed:
            groups.setdefault((stage.stage, r.reason), []).append(r)

    for (stage, reason), items in groups.items():
        if args.reason and reason not in args.reason:
            continue
        picked = rng.sample(items, min(args.n, len(items)))
        print(f"\n=== {stage} / {reason}  ({len(items)} removed, showing {len(picked)}) ===")
        for r in picked:
            print(f"  [{r.record_id}] {r.detail}")
            show_row(raw.get(r.record_id), args.chars)

    if args.redactions:
        for kind, rx, placeholder, validator in _PATTERNS:
            hits = [rec for rec in run.final if placeholder in rec.content()]
            picked = rng.sample(hits, min(args.n, len(hits)))
            print(f"\n=== redaction {placeholder}  ({len(hits)} in final data, showing {len(picked)}) ===")
            for rec in picked:
                row = raw.get(rec.id)
                found = []
                if row:
                    found = [
                        m.group() for m in rx.finditer(raw_content(row))
                        if validator is None or validator(m)
                    ]
                content = rec.content()
                i = content.find(placeholder)
                print(f"  [{rec.id}] matched: {found}")
                print(f"    context: {oneline(content[max(0, i - 80): i + 80], 200)}")


if __name__ == "__main__":
    main()