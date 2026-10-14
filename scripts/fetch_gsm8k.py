import json
from pathlib import Path

from datasets import load_dataset

OUT = Path("data/benchmarks/gsm8k.jsonl")


def main() -> None:
    ds = load_dataset("openai/gsm8k", "main", split="test")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for row in ds:
            f.write(json.dumps({"text": row["question"]}, ensure_ascii=False) + "\n")
    print(f"wrote {len(ds)} questions to {OUT}")


if __name__ == "__main__":
    main()