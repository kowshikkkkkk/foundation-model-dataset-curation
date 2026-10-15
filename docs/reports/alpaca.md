# Dataset Quality Report

## Summary

- **Dataset version:** `f5e5c6383579`
- **Created (UTC):** 2026-10-15T06:34:12+00:00
- **Config hash:** `180860fbdfa8`
- **Git commit:** `f15a698a449b322732461b9ebe24351a6dd1c9ba` (uncommitted changes: False)
- **Input lines parsed:** 52002
- **Records in curated dataset:** 51972 (99.9% retained)
- **Records removed:** 30

## Funnel

| Stage | In | Out | Removed | Retained vs raw |
|---|---|---|---|---|
| ingest | 52002 | 51974 | 28 | 99.9% |
| normalize | 51974 | 51974 | 0 | 99.9% |
| quality | 51974 | 51974 | 0 | 99.9% |
| safety | 51974 | 51974 | 0 | 99.9% |
| language | 51974 | 51974 | 0 | 99.9% |
| contamination | 51974 | 51974 | 0 | 99.9% |
| exact_dedup | 51974 | 51974 | 0 | 99.9% |
| near_dedup | 51974 | 51972 | 2 | 99.9% |

## Removal reasons

| Stage | Reason | Count | Share of raw input |
|---|---|---|---|
| ingest | schema_invalid | 28 | 0.1% |
| near_dedup | near_duplicate | 2 | 0.0% |

## Sample removals

- `ingest` / `schema_invalid`: record `alpaca-284`: Value error, instruction records require 'instruction' and 'response'
- `ingest` / `schema_invalid`: record `alpaca-1223`: Value error, instruction records require 'instruction' and 'response'
- `ingest` / `schema_invalid`: record `alpaca-1347`: Value error, instruction records require 'instruction' and 'response'
- `near_dedup` / `near_duplicate`: record `alpaca-21762`: ~0.68 similar to alpaca-1
- `near_dedup` / `near_duplicate`: record `alpaca-27354`: ~0.98 similar to alpaca-20345

## Stage counters

- **safety**: redacted_email: 41, records_redacted: 21, redacted_phone: 1
- **language**: und_too_short: 40322, lang_en: 11589, und_low_confidence: 63
- **contamination**: benchmark_ngrams: 46293, too_short_to_check: 1921

## Before and after

| Metric | Before | After |
|---|---|---|
| Records | 51974 | 51972 |
| Total characters | 18499763 | 18426428 |
| Mean characters | 355.9 | 354.5 |
| Median characters | 278.0 | 276.0 |
| P95 characters | 841 | 838 |
| Tokens | 3064786 | 3064250 |
| Vocabulary size | 46289 | 46236 |
| distinct-1 | 0.0151 | 0.0151 |
| distinct-2 | 0.2421 | 0.2421 |

| Distribution | Before | After |
|---|---|---|
| Record kinds | instruction: 51974 | instruction: 51972 |
| Sources | data/raw/alpaca.jsonl: 51974 | data/raw/alpaca.jsonl: 51972 |
| Languages | - | und: 40383, en: 11589 |

## Notes

- *Before* is the set of records that parsed and validated at ingest; malformed lines never became records.
- Language is detected after normalization, so *before* has no language counts. See the language stage counters for the distribution of records entering that stage.
- distinct-n is unique n-grams divided by total n-grams. It depends on corpus size and rises mechanically when duplicates are removed, so read it as a description of the data, not a quality score.
- Quality and language thresholds are untuned defaults until they are checked against hand-labeled samples.

## Outputs

| Format | Path | Bytes | SHA-256 |
|---|---|---|---|
| jsonl | data/curated/alpaca/curated.jsonl | 28217617 | `e61be4d4e4809e1723d9e5dc352b80c7906e6872fe0169d2c0f4300cf565cf6b` |
| parquet | data/curated/alpaca/curated.parquet | 8221951 | `ddbe69faec00e0e860c954ac3779b6ed4d54ff8e3a76cec9679692af96f14c50` |

## Reproducibility

- Python 3.11.9
- pydantic 2.14.1
- pyyaml 6.0.3
- datasketch 2.0.0
- langdetect 1.0.9
- pyarrow 26.0.0
- Benchmark data/benchmarks/gsm8k.jsonl sha256 `db1772dde7b8`
- Full configuration and input hashes are in `manifest.json`.
