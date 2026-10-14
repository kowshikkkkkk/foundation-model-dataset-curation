from __future__ import annotations

import json

import pytest

from curation import language
from curation.config import ContaminationConfig, DedupConfig, LanguageConfig
from curation.contamination import contamination_filter, load_benchmark_index
from curation.dedup import exact_dedup, near_dedup, shingles
from curation.language import language_filter
from curation.schema import Record


def doc(i: str, text: str) -> Record:
    return Record(id=i, kind="document", source="t", text=text)


def inst(i: str, q: str, a: str) -> Record:
    return Record(id=i, kind="instruction", source="t", instruction=q, response=a)


# ---------- dedup ----------

def test_exact_dedup_keeps_first_and_respects_kind():
    recs = [
        doc("a", "hello world"),
        doc("b", "hello world"),
        doc("c", "Hello world"),           # different case: not an exact duplicate
        inst("d", "q", "a"),
        doc("e", "q\n\na"),                # same joined text as d, but a different kind
    ]
    r = exact_dedup(recs)
    assert [x.id for x in r.kept] == ["a", "c", "d", "e"]
    assert r.reason_counts() == {"exact_duplicate": 1}
    assert r.removed[0].detail == "duplicate of a"


def test_near_dedup_catches_small_edits_and_case():
    words = [f"w{i}" for i in range(100)]
    a = " ".join(words)
    b = " ".join(words[:50] + ["CHANGED"] + words[51:])   # one word changed, similarity ~0.90
    c = " ".join(f"x{i}" for i in range(100))             # unrelated
    d = a.upper()                                         # same text, different case

    recs = [doc("a", a), doc("b", b), doc("c", c), doc("d", d)]
    r = near_dedup(recs, DedupConfig(), seed=42)

    assert [x.id for x in r.kept] == ["a", "c"]
    assert {x.record_id for x in r.removed} == {"b", "d"}
    assert r.reason_counts() == {"near_duplicate": 2}


def test_records_without_tokens_are_not_matched_to_each_other():
    r = near_dedup([doc("a", "!!!"), doc("b", "???")], DedupConfig(), seed=42)
    assert r.n_out == 2


def test_shingles():
    assert shingles("The cat sat", 5) == {"the cat sat"}   # shorter than one window
    assert len(shingles("a b c d e f", 5)) == 2
    assert shingles("!!!", 5) == set()


# ---------- language (detector replaced by a stub) ----------

CFG = LanguageConfig(allowed=("en",), min_confidence=0.9, min_detect_chars=40)


def test_instruction_language_is_judged_on_the_prompt(monkeypatch):
    def fake(text, seed):
        return ("fr", 0.99) if "bonjour" in text else ("en", 0.99)

    monkeypatch.setattr(language, "detect_language", fake)

    english_prompt_french_answer = inst(
        "a",
        "Write a short paragraph about the history of the French Revolution.",
        "bonjour tout le monde, comment allez-vous aujourd'hui",
    )
    french_document = doc("b", "bonjour tout le monde, comment allez-vous aujourd'hui mes amis")

    r = language_filter([english_prompt_french_answer, french_document], CFG, seed=42)

    assert [x.id for x in r.kept] == ["a"]
    assert r.kept[0].meta["lang"] == "en"
    assert r.reason_counts() == {"language_not_allowed": 1}
    assert r.removed[0].record_id == "b"


def test_short_text_is_tagged_und_without_calling_the_detector(monkeypatch):
    def boom(text, seed):
        raise AssertionError("detector must not run on short text")

    monkeypatch.setattr(language, "detect_language", boom)
    r = language_filter([doc("a", "short text")], CFG, seed=42)

    assert r.n_out == 1 and r.kept[0].meta["lang"] == "und"
    assert r.stats == {"und_too_short": 1}


def test_low_confidence_is_kept_as_und(monkeypatch):
    monkeypatch.setattr(language, "detect_language", lambda text, seed: ("fr", 0.5))
    r = language_filter([doc("a", "x" * 60)], CFG, seed=42)

    assert r.n_out == 1 and r.kept[0].meta["lang"] == "und"
    assert r.stats == {"und_low_confidence": 1}


def test_undetectable_text_is_kept_as_und(monkeypatch):
    monkeypatch.setattr(language, "detect_language", lambda text, seed: None)
    r = language_filter([doc("a", "x" * 60)], CFG, seed=42)

    assert r.n_out == 1 and r.kept[0].meta["lang"] == "und"
    assert r.stats == {"und_undetected": 1}


def test_confident_allowed_language_is_tagged_and_kept(monkeypatch):
    monkeypatch.setattr(language, "detect_language", lambda text, seed: ("en", 0.95))
    r = language_filter([doc("a", "x" * 60)], CFG, seed=42)

    assert r.kept[0].meta["lang"] == "en" and r.kept[0].meta["lang_conf"] == 0.95
    assert r.stats == {"lang_en": 1}


# ---------- contamination ----------

QUESTION = (
    "Maria bought 12 notebooks in March and then bought one third as many in April. "
    "How many notebooks did Maria buy in total during March and April?"
)


def test_contamination_finds_verbatim_and_embedded_but_not_paraphrase(tmp_path):
    (tmp_path / "testbench.jsonl").write_text(json.dumps({"text": QUESTION}) + "\n", encoding="utf-8")
    cfg = ContaminationConfig(ngram_size=13, benchmarks=("testbench",), benchmark_dir=str(tmp_path))
    index = load_benchmark_index(cfg)

    recs = [
        inst("leak", "Solve this.", QUESTION),
        doc("embedded", "Here is a worksheet. " + QUESTION + " Show your work."),
        doc(
            "paraphrase",
            "Maria purchased 12 notebooks during March and a third of that amount in April. "
            "What is the total number of notebooks she bought?",
        ),
        doc("short", "Maria bought 12 notebooks"),
    ]
    r = contamination_filter(recs, index, 13)

    assert [x.id for x in r.kept] == ["paraphrase", "short"]
    assert {x.record_id for x in r.removed} == {"leak", "embedded"}
    assert r.reason_counts() == {"benchmark_contamination": 2}
    assert r.removed[0].detail.startswith("testbench:")
    assert r.stats == {"benchmark_ngrams": 15, "hits_testbench": 2, "too_short_to_check": 1}


def test_missing_benchmark_file_fails_loudly(tmp_path):
    cfg = ContaminationConfig(benchmarks=("nope",), benchmark_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_benchmark_index(cfg)