from __future__ import annotations

import re
from typing import Iterable

from curation.config import SafetyConfig
from curation.result import Removed, StageResult
from curation.schema import Record

STAGE_SAFETY = "safety"
_FIELDS = ("text", "instruction", "response")

# Verhoeff checksum tables (used by Aadhaar).
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff(number: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_AADHAAR = re.compile(
    r"(?<!\d)(?<!\d[ -])[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?![ -]?\d)"
)
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_PHONE = re.compile(r"(?<!\d)(?:\+91[ -]?|91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}(?!\d)")

_RESERVED_DOMAINS = {"example.com", "example.org", "example.net"}
_RESERVED_TLDS = {"example", "test", "invalid", "localhost"}
_PHONE_CONTEXT = re.compile(r"phone|mobile|\bcall|contact|\btel\b|whatsapp|\bcell\b|\bph\b")
_BARE_PHONE = re.compile(r"[6-9]\d{9}")


# Validators take the regex match and return True if it should be redacted.
def _email_ok(m: re.Match) -> bool:
    labels = m.group().rsplit("@", 1)[1].lower().split(".")
    if labels[-1] in _RESERVED_TLDS or ".".join(labels[-2:]) in _RESERVED_DOMAINS:
        return False
    return True


def _aadhaar_ok(m: re.Match) -> bool:
    return verhoeff(re.sub(r"[ -]", "", m.group()))


def _phone_ok(m: re.Match) -> bool:
    if not _BARE_PHONE.fullmatch(m.group()):
        return True  # has a prefix or a separator
    window = m.string[max(0, m.start() - 30): m.start()].lower()
    return bool(_PHONE_CONTEXT.search(window))


# Order matters: email first, Aadhaar before phone (a failed Aadhaar can still be a phone).
_PATTERNS = [
    ("email", _EMAIL, "[EMAIL]", _email_ok),
    ("aadhaar", _AADHAAR, "[AADHAAR]", _aadhaar_ok),
    ("pan", _PAN, "[PAN]", None),
    ("phone", _PHONE, "[PHONE]", _phone_ok),
]


def scrub(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}

    def make(kind, placeholder, validator):
        def repl(m):
            if validator and not validator(m):
                return m.group()
            counts[kind] = counts.get(kind, 0) + 1
            return placeholder
        return repl

    for kind, rx, placeholder, validator in _PATTERNS:
        text = rx.sub(make(kind, placeholder, validator), text)
    return text, counts


def _blocklist_regex(terms: tuple[str, ...]):
    if not terms:
        return None
    pattern = r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b"
    return re.compile(pattern, re.IGNORECASE)


def safety_filter(records: Iterable[Record], cfg: SafetyConfig) -> StageResult:
    result = StageResult(stage=STAGE_SAFETY)
    block = _blocklist_regex(cfg.blocklist)

    for rec in records:
        if block:
            m = block.search(rec.content())
            if m:
                result.removed.append(
                    Removed(rec.id, STAGE_SAFETY, "blocklist_term", m.group().lower())
                )
                continue

        update: dict[str, str] = {}
        counts: dict[str, int] = {}
        for f in _FIELDS:
            val = getattr(rec, f)
            if val is None:
                continue
            new, c = scrub(val)
            update[f] = new
            for k, n in c.items():
                counts[k] = counts.get(k, 0) + n

        if not counts:
            result.kept.append(rec)
            continue

        if cfg.pii_action == "drop":
            result.removed.append(
                Removed(rec.id, STAGE_SAFETY, "pii_detected", ",".join(sorted(counts)))
            )
            continue

        result.stats["records_redacted"] = result.stats.get("records_redacted", 0) + 1
        for k, n in counts.items():
            key = f"redacted_{k}"
            result.stats[key] = result.stats.get(key, 0) + n
        result.kept.append(Record(**{**rec.model_dump(), **update}))

    return result