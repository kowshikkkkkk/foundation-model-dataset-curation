from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from pydantic import ValidationError

from curation.config import NormalizeConfig
from curation.result import Removed, StageResult
from curation.schema import Record

STAGE = "normalize"

# Not U+200C / U+200D: they are meaningful in Indic scripts.
_ZERO_WIDTH = {"\u200b", "\ufeff"}
_SPACES = re.compile(r"[ \t\u00a0]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")
_FIELDS = ("text", "instruction", "response")


def normalize_text(s: str, cfg: NormalizeConfig) -> str:
    s = unicodedata.normalize(cfg.unicode_form, s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "".join(
        ch for ch in s
        if ch not in _ZERO_WIDTH
        and (ch in "\n\t" or unicodedata.category(ch) != "Cc")
    )
    if cfg.collapse_whitespace:
        s = _SPACES.sub(" ", s)
        s = "\n".join(line.strip() for line in s.split("\n"))
        s = _MANY_NEWLINES.sub("\n\n", s)
    return s.strip()


def normalize(records: Iterable[Record], cfg: NormalizeConfig) -> StageResult:
    result = StageResult(stage=STAGE)
    for rec in records:
        update = {
            f: normalize_text(getattr(rec, f), cfg)
            for f in _FIELDS
            if getattr(rec, f) is not None
        }
        try:
            new = Record(**{**rec.model_dump(), **update})
        except ValidationError:
            result.removed.append(Removed(rec.id, STAGE, "empty_after_normalize"))
            continue
        result.kept.append(new)
    return result