from __future__ import annotations

import unicodedata
from typing import Iterable

from curation.config import QualityConfig
from curation.result import Removed, StageResult
from curation.schema import Record

STAGE_QUALITY = "quality"
_INSTRUCTION_MIN_LINE = 20  # chars; shorter lines are ignored for instruction records

def alpha_ratio(text: str) -> float:
    """Share of non-whitespace characters that are letters or combining marks."""
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    letters = sum(1 for c in chars if unicodedata.category(c)[0] in ("L", "M"))
    return letters / len(chars)


def line_repetition(text: str, min_len: int = 0) -> float:
    """Share of qualifying lines that repeat an earlier line."""
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln and len(ln) >= min_len]
    if len(lines) < 2:
        return 0.0
    return 1 - len(set(lines)) / len(lines)


def _check(rec: Record, cfg: QualityConfig) -> tuple[str, str] | None:
    text = rec.content()
    n = len(text)
    is_doc = rec.kind == "document"
    min_chars = cfg.min_chars if is_doc else cfg.min_chars_instruction
    max_rep = cfg.max_line_repetition if is_doc else cfg.max_line_repetition_instruction

    if n < min_chars:
        return "too_short", f"len={n} < {min_chars}"
    if n > cfg.max_chars:
        return "too_long", f"len={n} > {cfg.max_chars}"

    if is_doc:
        a = alpha_ratio(text)
        if a < cfg.min_alpha_ratio:
            return "low_alpha_ratio", f"alpha={a:.3f} < {cfg.min_alpha_ratio:.2f}"
        fields, min_len = [rec.text or ""], 0
    else:
        fields, min_len = [rec.instruction or "", rec.response or ""], _INSTRUCTION_MIN_LINE

    rep = max(line_repetition(f, min_len) for f in fields)
    if rep > max_rep:
        return "high_line_repetition", f"repeated_lines={rep:.3f} > {max_rep:.2f}"
    return None


def quality_filter(records: Iterable[Record], cfg: QualityConfig) -> StageResult:
    result = StageResult(stage=STAGE_QUALITY)
    for rec in records:
        failure = _check(rec, cfg)
        if failure is None:
            result.kept.append(rec)
        else:
            reason, detail = failure
            result.removed.append(Removed(rec.id, STAGE_QUALITY, reason, detail))
    return result