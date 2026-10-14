from __future__ import annotations

from typing import Iterable

from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

from curation.config import LanguageConfig
from curation.result import Removed, StageResult
from curation.schema import Record

STAGE_LANG = "language"
_MAX_CHARS = 2000


def detect_language(text: str, seed: int) -> tuple[str, float] | None:
    """Return (language code, probability) or None if undetectable."""
    DetectorFactory.seed = seed  # reset per call so results don't depend on order
    try:
        top = detect_langs(text[:_MAX_CHARS])[0]
    except LangDetectException:
        return None
    return top.lang, top.prob


def _count(stats: dict[str, int], key: str) -> None:
    stats[key] = stats.get(key, 0) + 1


def language_filter(records: Iterable[Record], cfg: LanguageConfig, seed: int) -> StageResult:
    result = StageResult(stage=STAGE_LANG)
    allowed = set(cfg.allowed)

    for rec in records:
        found = detect_language(rec.content(), seed)
        if found is None:
            _count(result.stats, "lang_undetected")
            result.removed.append(Removed(rec.id, STAGE_LANG, "language_undetected"))
            continue

        lang, conf = found
        _count(result.stats, f"lang_{lang}")

        if lang not in allowed:
            result.removed.append(
                Removed(rec.id, STAGE_LANG, "language_not_allowed", f"{lang} ({conf:.2f})")
            )
        elif conf < cfg.min_confidence:
            result.removed.append(
                Removed(rec.id, STAGE_LANG, "language_low_confidence", f"{lang} ({conf:.2f})")
            )
        else:
            meta = {**rec.meta, "lang": lang, "lang_conf": round(conf, 3)}
            result.kept.append(Record(**{**rec.model_dump(), "meta": meta}))

    return result