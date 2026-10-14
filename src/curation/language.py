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


def _classify(text: str, cfg: LanguageConfig, seed: int) -> tuple[str, float, str | None]:
    """Return (lang, confidence, und_reason). lang is 'und' when we won't act on a detection."""
    if len(text) < cfg.min_detect_chars:
        return "und", 0.0, "und_too_short"
    found = detect_language(text, seed)
    if found is None:
        return "und", 0.0, "und_undetected"
    lang, conf = found
    if conf < cfg.min_confidence:
        return "und", conf, "und_low_confidence"
    return lang, conf, None


def language_filter(records: Iterable[Record], cfg: LanguageConfig, seed: int) -> StageResult:
    result = StageResult(stage=STAGE_LANG)
    allowed = set(cfg.allowed)

    for rec in records:
        basis = rec.instruction if rec.kind == "instruction" else rec.text
        lang, conf, und_reason = _classify(basis or "", cfg, seed)
        _count(result.stats, und_reason if und_reason else f"lang_{lang}")

        if lang != "und" and lang not in allowed:
            result.removed.append(
                Removed(rec.id, STAGE_LANG, "language_not_allowed", f"{lang} ({conf:.2f})")
            )
            continue

        meta = {**rec.meta, "lang": lang, "lang_conf": round(conf, 3)}
        result.kept.append(Record(**{**rec.model_dump(), "meta": meta}))

    return result