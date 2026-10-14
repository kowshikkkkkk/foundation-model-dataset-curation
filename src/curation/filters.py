from __future__ import annotations

import unicodedata
from typing import Iterable

from curation.config import QualityConfig
from curation.result import Removed, StageResult
from curation.schema import Record

STAGE_QUALITY = "quality"


def alpha_ratio(text: str) -> float:
    """Share of non-whitespace characters that are letters or combining marks."""
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    letters = sum(1 for c in chars if unicodedata.category(c)[0] in ("L", "M"))
    return letters / len(chars)


def line_repetition(text: str) -> float:
    """Share of non-empty lines that repeat an earlier line."""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(lines) < 2:
        return 0.0
    return 1 - len(set(lines)) / len(lines)


def _check(text: str, cfg: QualityConfig) -> tuple[str, str] | None:
    n = len(text)
    if n < cfg.min_chars:
        return "too_short", f"len={n} < {cfg.min_chars}"
    if n > cfg.max_chars:
        return "too_long", f"len={n} > {cfg.max_chars}"
    a = alpha_ratio(text)
    if a < cfg.min_alpha_ratio:
        return "low_alpha_ratio", f"alpha={a:.2f} < {cfg.min_alpha_ratio:.2f}"
    rep = line_repetition(text)
    if rep > cfg.max_line_repetition:
        return "high_line_repetition", f"repeated_lines={rep:.2f} > {cfg.max_line_repetition:.2f}"
    return None


def quality_filter(records: Iterable[Record], cfg: QualityConfig) -> StageResult:
    result = StageResult(stage=STAGE_QUALITY)
    for rec in records:
        failure = _check(rec.content(), cfg)
        if failure is None:
            result.kept.append(rec)
        else:
            reason, detail = failure
            result.removed.append(Removed(rec.id, STAGE_QUALITY, reason, detail))
    return result