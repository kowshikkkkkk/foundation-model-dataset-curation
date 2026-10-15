from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

VALID = {"drop", "keep", "skip", ""}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def read_csv(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="e.g. validation/wiki")
    d = Path(ap.parse_args().dir)

    labels = {r["id"]: r["label"].strip().lower() for r in read_csv(d / "label_sheet.csv")}
    bad = sorted(set(labels.values()) - VALID)
    if bad:
        sys.exit(f"unknown labels: {bad} (use drop, keep or skip)")
    n_blank = sum(1 for v in labels.values() if v == "")
    if n_blank:
        print(f"warning: {n_blank} unlabeled rows are treated as skip")

    groups = defaultdict(lambda: {"drop": 0, "keep": 0, "skip": 0, "pop": 0})
    for r in read_csv(d / "label_key.csv"):
        g = groups[r["group"]]
        g[labels.get(r["id"], "") or "skip"] += 1
        g["pop"] = int(r["population"])

    print(f"{'group':<48}{'n':>4}{'drop':>6}{'skip':>6}   precision (95% CI)")
    tp = tp_lo = tp_hi = 0.0
    scored_pop = 0
    for name in sorted(groups):
        if name == "kept":
            continue
        g = groups[name]
        n = g["drop"] + g["keep"]
        if n == 0:
            print(f"{name:<48}{n:>4}{g['drop']:>6}{g['skip']:>6}   n/a (all skipped)")
            continue
        p = g["drop"] / n
        lo, hi = wilson(g["drop"], n)
        tp += p * g["pop"]
        tp_lo += lo * g["pop"]
        tp_hi += hi * g["pop"]
        scored_pop += g["pop"]
        print(f"{name:<48}{n:>4}{g['drop']:>6}{g['skip']:>6}   {p:.2f} ({lo:.2f}-{hi:.2f})")

    k = groups.get("kept")
    if k is None:
        sys.exit("label_key.csv has no 'kept' group")
    n = k["drop"] + k["keep"]
    if n == 0:
        sys.exit("no labeled kept records")
    pop = k["pop"]
    miss = k["drop"] / n
    lo, hi = wilson(k["drop"], n)
    fn, fn_lo, fn_hi = miss * pop, lo * pop, hi * pop

    print(f"\nkept sample: {n} labeled, {k['drop']} defective")
    print(f"miss rate {miss:.3f} (95% CI {lo:.3f}-{hi:.3f})")
    print(f"implied missed records among {pop} kept: {fn:.0f} ({fn_lo:.0f}-{fn_hi:.0f})")

    if scored_pop:
        print(f"\noverall precision of removals: {tp / scored_pop:.2f} "
              f"({tp_lo / scored_pop:.2f}-{tp_hi / scored_pop:.2f}, interval is approximate)")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    r_lo = tp_lo / (tp_lo + fn_hi) if tp_lo + fn_hi else 0.0
    r_hi = tp_hi / (tp_hi + fn_lo) if tp_hi + fn_lo else 1.0
    print(f"estimated recall: {recall:.2f} (rough range {r_lo:.2f}-{r_hi:.2f})")


if __name__ == "__main__":
    main()