import json
from pathlib import Path

from datasets import load_dataset

OUT = Path("data/raw/wiki.jsonl")
SNAPSHOT = "20231101"
LANGS = {"en": 2000, "ta": 2000, "hi": 2000}


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for lang, limit in LANGS.items():
            ds = load_dataset(
                "wikimedia/wikipedia", f"{SNAPSHOT}.{lang}", split="train", streaming=True
            )
            count = 0
            for row in ds:
                text = row["text"].strip()
                if not text:
                    continue
                rec = {
                    "id": f"wiki-{lang}-{row['id']}",
                    "text": text,
                    "wiki_lang": lang,
                    "title": row["title"],
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                count += 1
                if count >= limit:
                    break
            print(lang, count)
            total += count
    print(f"wrote {total} articles to {OUT}")


if __name__ == "__main__":
    main()