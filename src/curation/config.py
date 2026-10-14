from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    # Unknown keys raise errors; instances are immutable.
    model_config = ConfigDict(extra="forbid", frozen=True)


class NormalizeConfig(_Base):
    unicode_form: Literal["NFC", "NFKC"] = "NFKC"
    collapse_whitespace: bool = True


class DedupConfig(_Base):
    shingle_size: int = Field(5, ge=1)       # words per shingle
    num_perm: int = Field(128, ge=16)        # MinHash signature length
    lsh_threshold: float = Field(0.8, gt=0, le=1)  # Jaccard cutoff


class QualityConfig(_Base):
    min_chars: int = Field(20, ge=0)
    max_chars: int = Field(100_000, ge=1)
    max_line_repetition: float = Field(0.3, ge=0, le=1)  # share of repeated lines
    min_alpha_ratio: float = Field(0.6, ge=0, le=1)      # share of letters


class LanguageConfig(_Base):
    allowed: tuple[str, ...] = ("en", "hi", "ta")
    min_confidence: float = Field(0.5, ge=0, le=1)


class ContaminationConfig(_Base):
    ngram_size: int = Field(13, ge=1)
    benchmarks: tuple[str, ...] = ("gsm8k",)

class SafetyConfig(_Base):
    pii_action: Literal["drop", "redact"] = "redact"
    blocklist: tuple[str, ...] = ()

class PipelineConfig(_Base):
    seed: int = 42
    input_paths: tuple[str, ...] = ()
    output_dir: str = "data/curated"

    normalize: NormalizeConfig = NormalizeConfig()
    dedup: DedupConfig = DedupConfig()
    quality: QualityConfig = QualityConfig()
    language: LanguageConfig = LanguageConfig()
    contamination: ContaminationConfig = ContaminationConfig()
    safety: SafetyConfig = SafetyConfig()

    def config_hash(self) -> str:
        """SHA-256 of the settings that affect pipeline behavior."""
        payload = self.model_dump(mode="json", exclude={"input_paths", "output_dir"})
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_config(path: str | Path) -> PipelineConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return PipelineConfig(**raw)