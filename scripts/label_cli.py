from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

FIELDS = ["id", "content", "label"]
NAMES = {"d": "drop", "k": "keep", "s": "skip"}


def save(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = Path(sys.argv[1]) / "label_sheet.csv"
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    todo = [r for r in rows if not r["label"].strip()]
    done = len(rows) - len(todo)
    print(f"{done} labeled, {len(todo)} to go. See RUBRIC.md for what drop means.")

    for n, r in enumerate(todo, 1):
        print("\n" + "=" * 70)
        print(f"[{done + n}/{len(rows)}] {r['id']}")
        print(r["content"])
        ans = ""
        while ans not in {"d", "k", "s", "q"}:
            ans = input("d=drop  k=keep  s=skip  q=quit > ").strip().lower()
        if ans == "q":
            break
        r["label"] = NAMES[ans]
        save(path, rows)

    print("\nsaved.")


if __name__ == "__main__":
    main()