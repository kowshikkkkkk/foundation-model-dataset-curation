# Dataset Quality Report

## Summary

- **Dataset version:** `b0ca2ba4fcfe`
- **Created (UTC):** 2026-10-15T06:32:18+00:00
- **Config hash:** `2f9a16295667`
- **Git commit:** `f15a698a449b322732461b9ebe24351a6dd1c9ba` (uncommitted changes: False)
- **Input lines parsed:** 6000
- **Records in curated dataset:** 5984 (99.7% retained)
- **Records removed:** 16

## Funnel

| Stage | In | Out | Removed | Retained vs raw |
|---|---|---|---|---|
| ingest | 6000 | 6000 | 0 | 100.0% |
| normalize | 6000 | 6000 | 0 | 100.0% |
| quality | 6000 | 5988 | 12 | 99.8% |
| safety | 5988 | 5988 | 0 | 99.8% |
| language | 5988 | 5987 | 1 | 99.8% |
| exact_dedup | 5987 | 5987 | 0 | 99.8% |
| near_dedup | 5987 | 5984 | 3 | 99.7% |

## Removal reasons

| Stage | Reason | Count | Share of raw input |
|---|---|---|---|
| quality | too_short | 6 | 0.1% |
| near_dedup | near_duplicate | 3 | 0.1% |
| quality | high_line_repetition | 3 | 0.1% |
| quality | low_alpha_ratio | 3 | 0.1% |
| language | language_not_allowed | 1 | 0.0% |

## Sample removals

- `quality` / `low_alpha_ratio`: record `wiki-ta-616`: alpha=0.478 < 0.60
- `quality` / `low_alpha_ratio`: record `wiki-ta-5272`: alpha=0.495 < 0.60
- `quality` / `low_alpha_ratio`: record `wiki-hi-6851`: alpha=0.593 < 0.60
- `quality` / `high_line_repetition`: record `wiki-ta-629`: repeated_lines=0.956 > 0.50
- `quality` / `high_line_repetition`: record `wiki-hi-5114`: repeated_lines=0.717 > 0.50
- `quality` / `high_line_repetition`: record `wiki-hi-6350`: repeated_lines=0.627 > 0.50
- `quality` / `too_short`: record `wiki-ta-6377`: len=19 < 20
- `quality` / `too_short`: record `wiki-ta-6754`: len=19 < 20
- `quality` / `too_short`: record `wiki-ta-7306`: len=14 < 20
- `language` / `language_not_allowed`: record `wiki-hi-2461`: ne (1.00)
- `near_dedup` / `near_duplicate`: record `wiki-hi-2889`: ~0.72 similar to wiki-hi-2879
- `near_dedup` / `near_duplicate`: record `wiki-hi-6994`: ~0.86 similar to wiki-hi-6992
- `near_dedup` / `near_duplicate`: record `wiki-hi-7238`: ~0.88 similar to wiki-hi-7235

## Stage counters

- **safety**: redacted_email: 11, records_redacted: 6, redacted_phone: 2
- **language**: lang_en: 2005, lang_ta: 1985, lang_hi: 1961, und_low_confidence: 30, und_too_short: 6, lang_ne: 1

## Before and after

| Metric | Before | After |
|---|---|---|
| Records | 6000 | 5984 |
| Total characters | 66144032 | 65857529 |
| Mean characters | 11024.0 | 11005.6 |
| Median characters | 4514.5 | 4507.0 |
| P95 characters | 46263 | 46140 |
| Tokens | 10356887 | 10351069 |
| Vocabulary size | 493751 | 493061 |
| distinct-1 | 0.0477 | 0.0476 |
| distinct-2 | 0.3992 | 0.3992 |

| Distribution | Before | After |
|---|---|---|
| Record kinds | document: 6000 | document: 5984 |
| Sources | data/raw/wiki.jsonl: 6000 | data/raw/wiki.jsonl: 5984 |
| Languages | - | en: 2005, ta: 1985, hi: 1958, und: 36 |

## Notes

- *Before* is the set of records that parsed and validated at ingest; malformed lines never became records.
- Language is detected after normalization, so *before* has no language counts. See the language stage counters for the distribution of records entering that stage.
- distinct-n is unique n-grams divided by total n-grams. It depends on corpus size and rises mechanically when duplicates are removed, so read it as a description of the data, not a quality score.
- Quality and language thresholds are untuned defaults until they are checked against hand-labeled samples.

## Outputs

| Format | Path | Bytes | SHA-256 |
|---|---|---|---|
| jsonl | data/curated/wiki/curated.jsonl | 103203151 | `c944fc6f161406e6055fa235d47aaa7ae7f13bc0db7a2d99e267bf0b21f10b9f` |
| parquet | data/curated/wiki/curated.parquet | 31230093 | `bc92d4c139b8c2d7a09d1cb26750136cc861f32d04c34dc60c5ed8d1a828a231` |

## Reproducibility

- Python 3.11.9
- pydantic 2.14.1
- pyyaml 6.0.3
- datasketch 2.0.0
- langdetect 1.0.9
- pyarrow 26.0.0
- Full configuration and input hashes are in `manifest.json`.
