from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from curation.config import load_config
from curation.pipeline import run_pipeline

PREVIEW_CHARS = 400

RUBRIC = """# Labeling rubric

Fill the `label` column of label_sheet.csv with one word per record:

- **drop**: a reviewer would NOT want this record in a training set because of a
  defect this pipeline targets: malformed or empty content, boilerplate or spam,
  endless repetition, gibberish, text in a language outside the allowed set,
  personal data, leaked benchmark text, or a near-copy of another record.
  Navigation or date-only stubs with no running text count as drop.
- **keep**: none of those defects apply.
- **skip**: you cannot judge it (for example, you cannot read the language).

Do not label drop for reasons the pipeline does not target: factual mistakes,
mediocre but valid answers, or opinions you disagree with.

Judge each record on its own. The sheet is shuffled and does not show which
filter handled it. Do not edit the `id` column.
"""


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


def preview(row: dict) -> str:
    parts = []
    for key in ("text", "instruction", "response", "output"):
        if key in row:
            val = str(row[key])
            cut = val[:PREVIEW_CHARS] + (" [...]" if len(val) > PREVIEW_CHARS else "")
            parts.append(f"[{key}] {cut}")
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--per-group", type=int, default=25, help="max records per removal group")
    ap.add_argument("--kept", type=int, default=100, help="records sampled from the kept set")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    cfg = load_config(args.config)
    raw = load_raw(cfg.input_paths)
    run = run_pipeline(cfg)
    rng = random.Random(args.seed)

    groups: dict[str, list[str]] = {}
    details: dict[str, str] = {}
    for stage in run.stages:
        for r in stage.removed:
            g = f"removed:{stage.stage}/{r.reason}"
            groups.setdefault(g, []).append(r.record_id)
            details[r.record_id] = r.detail
    groups["kept"] = [rec.id for rec in run.final]

    rows: list[tuple[str, str, int]] = []
    skipped = 0
    for g in sorted(groups):
        ids = sorted(i for i in groups[g] if i in raw)
        skipped += len(groups[g]) - len(ids)
        k = args.kept if g == "kept" else args.per_group
        sample = rng.sample(ids, min(k, len(ids)))
        print(f"{g:<48}{len(sample):>4}/{len(groups[g])}")
        rows += [(i, g, len(groups[g])) for i in sample]
    print(f"skipped (no raw row): {skipped}")

    rng.shuffle(rows)

    out = Path("validation") / Path(args.config).stem
    out.mkdir(parents=True, exist_ok=True)

    with open(out / "label_sheet.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "content", "label"])
        for rid, _, _ in rows:
            w.writerow([rid, preview(raw[rid]), ""])

    with open(out / "label_key.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "group", "population", "detail"])
        for rid, g, pop in rows:
            w.writerow([rid, g, pop, details.get(rid, "")])

    (out / "RUBRIC.md").write_text(RUBRIC, encoding="utf-8")
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()