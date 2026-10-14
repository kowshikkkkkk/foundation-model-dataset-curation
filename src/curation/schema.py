from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


class Record(BaseModel):
    """Unified record for raw documents and instruction-response pairs."""

    id: str
    kind: Literal["document", "instruction"]
    source: str  # provenance: file path or dataset name

    # kind == "document"
    text: Optional[str] = None

    # kind == "instruction"
    instruction: Optional[str] = None
    response: Optional[str] = None

    meta: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_fields_match_kind(self) -> "Record":
        if self.kind == "document" and not self.text:
            raise ValueError("document records require non-empty 'text'")
        if self.kind == "instruction" and not (self.instruction and self.response):
            raise ValueError("instruction records require 'instruction' and 'response'")
        return self

    def content(self) -> str:
        """Canonical text used by dedup, language ID, and quality filters."""
        if self.kind == "document":
            return self.text or ""
        return f"{self.instruction}\n\n{self.response}"