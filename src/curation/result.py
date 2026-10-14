from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from curation.schema import Record


@dataclass(frozen=True)
class Removed:
    record_id: str
    stage: str
    reason: str          # short code, e.g. "schema_invalid"
    detail: str = ""     # optional human-readable context


@dataclass
class StageResult:
    stage: str
    kept: list[Record] = field(default_factory=list)
    removed: list[Removed] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)  # extra counters, e.g. redactions

    @property
    def n_in(self) -> int:
        return len(self.kept) + len(self.removed)

    @property
    def n_out(self) -> int:
        return len(self.kept)

    def reason_counts(self) -> dict[str, int]:
        return dict(Counter(r.reason for r in self.removed))