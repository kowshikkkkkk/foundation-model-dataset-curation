import json
from pathlib import Path

from datasets import load_dataset

OUT = Path("data/raw/alpaca.jsonl")


def main() -> None:
    ds = load_dataset("tatsu-lab/alpaca", split="train")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for i, row in enumerate(ds):
            instruction = row["instruction"].strip()
            extra = row["input"].strip()
            if extra:
                instruction = f"{instruction}\n\n{extra}"
            rec = {"id": f"alpaca-{i}", "instruction": instruction, "response": row["output"]}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(ds)} rows to {OUT}")


if __name__ == "__main__":
    main()