from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

from curation.config import ContaminationConfig, LanguageConfig, PipelineConfig
from curation.pipeline import run_pipeline
from score_labels import wilson

N = 20
N_BASE = 40
SYMBOLS = "!?#$%^&*()[]{}<>~|"
FR = [
    "Le gouvernement a annoncé hier une nouvelle série de mesures pour soutenir les petites entreprises.",
    "La ville est connue pour son architecture ancienne et ses nombreux musées ouverts toute l'année.",
    "Les enfants jouent dans le jardin pendant que leurs parents préparent le repas du soir.",
    "Cette année, la récolte de raisin a été particulièrement abondante dans toute la région.",
    "Le train de nuit part de la gare centrale à vingt-deux heures et arrive demain matin.",
    "Mon frère travaille dans une petite librairie près de la rivière depuis plusieurs années.",
]
EXPECTED = {
    "exact_dup": ("exact_dedup", "exact_duplicate"),
    "near_dup": ("near_dedup", "near_duplicate"),
    "junk": ("quality", "low_alpha_ratio"),
    "loop": ("quality", "high_line_repetition"),
    "too_short": ("quality", "too_short"),
    "contamination": ("contamination", "benchmark_contamination"),
    "foreign": ("language", "language_not_allowed"),
}


def load_pool(n: int) -> list[str]:
    pool: list[str] = []
    with open("data/raw/wiki.jsonl", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if not row["id"].startswith("wiki-en-"):
                continue
            words = row["text"].split()
            if len(words) >= 150:
                pool.append(" ".join(words[:150]))
            if len(pool) == n:
                return pool
    sys.exit(f"need {n} English wiki articles of 150+ words, found {len(pool)}")


def load_questions(n: int) -> list[str]:
    with open("data/benchmarks/gsm8k.jsonl", encoding="utf-8") as f:
        return [json.loads(line)["text"] for line in list(f)[:n]]


def main() -> None:
    rng = random.Random(0)
    P = load_pool(100)
    Q = load_questions(N)

    base = [{"id": f"base-{i}", "text": P[i]} for i in range(N_BASE)]
    plants = []
    for i in range(N):
        near = P[20 + i].split()
        near[len(near) // 2] = "CHANGED"
        line = " ".join(P[80 + i].split()[:12])
        junk = " ".join("".join(rng.choice(SYMBOLS) for _ in range(6)) for _ in range(10))
        plants += [
            {"id": f"plant-exact_dup-{i}", "text": P[i]},
            {"id": f"plant-near_dup-{i}", "text": " ".join(near)},
            {"id": f"plant-junk-{i}", "text": junk},
            {"id": f"plant-loop-{i}", "text": "\n".join([line] * 10)},
            {"id": f"plant-too_short-{i}", "text": f"short note {i}"},
            {"id": f"plant-pii-{i}", "text": P[40 + i] + f" Contact person{i}@gmail.com for details."},
            {"id": f"plant-contamination-{i}", "text": P[60 + i] + " " + Q[i]},
            {"id": f"plant-foreign-{i}", "text": " ".join(rng.sample(FR, 3))},
        ]

    out_dir = Path("data/curated/_planted")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "input.jsonl"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in base + plants:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    cfg = PipelineConfig(
        input_paths=(str(path),),
        output_dir=str(out_dir),
        language=LanguageConfig(allowed=("en",)),
        contamination=ContaminationConfig(benchmarks=("gsm8k",)),
    )
    run = run_pipeline(cfg)
    removed = {r.record_id: (s.stage, r.reason) for s in run.stages for r in s.removed}
    final = {rec.id: rec for rec in run.final}

    print(f"{'defect':<15}{'n':>4}{'caught':>8}  {'95% CI':<11}other outcomes")
    for kind in [*EXPECTED, "pii"]:
        ids = [p["id"] for p in plants if p["id"].startswith(f"plant-{kind}-")]
        caught = 0
        other: Counter = Counter()
        for rid in ids:
            if kind == "pii":
                rec = final.get(rid)
                text = rec.content() if rec else ""
                ok = rec is not None and "[EMAIL]" in text and "@gmail.com" not in text
                got = removed.get(rid, ("kept", "unredacted"))
            else:
                got = removed.get(rid, ("kept", "-"))
                ok = got == EXPECTED[kind]
            if ok:
                caught += 1
            else:
                other[f"{got[0]}/{got[1]}"] += 1
        lo, hi = wilson(caught, len(ids))
        print(f"{kind:<15}{len(ids):>4}{caught:>8}  {lo:.2f}-{hi:.2f}   {dict(other) or ''}")

    wrong = Counter(f"{s}/{r}" for rid, (s, r) in removed.items() if rid.startswith("base-"))
    print(f"\nclean base records removed: {sum(wrong.values())}/{N_BASE} {dict(wrong) or ''}")


if __name__ == "__main__":
    main()