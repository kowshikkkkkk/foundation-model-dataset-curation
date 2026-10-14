from __future__ import annotations

from curation.config import NormalizeConfig, QualityConfig, SafetyConfig
from curation.filters import quality_filter
from curation.normalize import normalize, normalize_text
from curation.safety import safety_filter, scrub, verhoeff
from curation.schema import Record

QC = QualityConfig(max_line_repetition_instruction=0.8)
NC = NormalizeConfig()


def doc(i: str, text: str) -> Record:
    return Record(id=i, kind="document", source="t", text=text)


def inst(i: str, q: str, a: str) -> Record:
    return Record(id=i, kind="instruction", source="t", instruction=q, response=a)


def quality(rec: Record) -> tuple[bool, str | None]:
    r = quality_filter([rec], QC)
    return r.n_out == 1, (r.removed[0].reason if r.removed else None)


# ---------- quality filters ----------

def test_short_instruction_answer_is_kept():
    # Alpaca: "What is 3 + 4?" -> "7" was wrongly dropped by a 20-char floor.
    assert quality(inst("a", "What is 3 + 4?", "7")) == (True, None)


def test_tiny_instruction_is_removed():
    assert quality(inst("a", "Hi", "A")) == (False, "too_short")


def test_short_document_is_removed():
    assert quality(doc("a", "Too short")) == (False, "too_short")


def test_song_with_repeated_chorus_is_kept():
    lines = [f"Verse line number {i} with enough length" for i in range(5)]
    song = "\n".join(lines + [lines[0]] * 3)  # 3 of 8 lines repeat
    assert quality(inst("a", "Write a song.", song)) == (True, None)


def test_instruction_loop_is_removed():
    loop = "This is a long repeated sentence that loops.\n" * 10
    assert quality(inst("a", "Write something.", loop)) == (False, "high_line_repetition")


def test_echoed_input_is_not_repetition():
    # The response repeats a line from the instruction; each field is checked on its own.
    line = "This evening I'll be going for a walk in the park."
    rec = inst("a", f"Convert to American English.\n\n{line}", line)
    assert quality(rec) == (True, None)


def test_document_menu_repetition_is_removed():
    assert quality(doc("a", "buy now\n" * 5)) == (False, "high_line_repetition")


def test_document_symbol_junk_is_removed():
    assert quality(doc("a", "!!!! ???? #### $$$$ %%%% ^^^^")) == (False, "low_alpha_ratio")


def test_instruction_with_numbers_is_not_judged_by_letter_ratio():
    rec = inst("a", "Format the following phone number.\n\n9094561234", "(909) 456-1234")
    assert quality(rec) == (True, None)


# ---------- safety ----------

def test_reserved_email_domains_are_not_redacted():
    assert scrub("Relay a@mail.example.org and b@host.invalid")[1] == {}
    text, counts = scrub("Mail john@example.com or jane@gmail.com")
    assert text == "Mail john@example.com or [EMAIL]"
    assert counts == {"email": 1}


def test_verhoeff_checksum():
    assert verhoeff("234567890124")
    assert not verhoeff("234567890123")


def test_aadhaar_needs_valid_checksum_and_clean_boundary():
    text, counts = scrub("Aadhaar 2345 6789 0124, bad one 2345 6789 0123")
    assert counts == {"aadhaar": 1}
    assert "[AADHAAR]" in text and "2345 6789 0123" in text
    # Card numbers must not be read as Aadhaar by matching a 12-digit slice.
    assert scrub("Card 5309 7677 8244 1346")[1] == {}
    assert scrub("Card 4298113234564582")[1] == {}


def test_bare_phone_needs_a_keyword_but_prefixed_does_not():
    assert scrub("Call 9876543210 today") == ("Call [PHONE] today", {"phone": 1})
    assert scrub("Order id 9876543210 shipped")[1] == {}
    assert scrub("Reach me on +91 98765 43210")[1] == {"phone": 1}


def test_pii_redact_versus_drop():
    rec = doc("a", "Contact jane@gmail.com for the details about this please.")

    red = safety_filter([rec], SafetyConfig(pii_action="redact"))
    assert red.n_out == 1 and "[EMAIL]" in red.kept[0].text
    assert red.stats["redacted_email"] == 1

    drp = safety_filter([rec], SafetyConfig(pii_action="drop"))
    assert drp.n_out == 0 and drp.reason_counts() == {"pii_detected": 1}


def test_blocklist_matches_whole_words_only():
    cfg = SafetyConfig(blocklist=("forbidden",))
    hit = safety_filter([doc("a", "This contains the word forbidden here.")], cfg)
    miss = safety_filter([doc("b", "This is forbiddenly fine to keep.")], cfg)
    assert hit.reason_counts() == {"blocklist_term": 1}
    assert miss.n_out == 1


# ---------- normalize ----------

def test_zero_width_space_removed_but_joiner_preserved():
    assert normalize_text("Hello\u200bworld", NC) == "Helloworld"
    # U+200D changes how Indic letters join, so it must survive.
    assert len(normalize_text("a\u200db", NC)) == 3


def test_nfkc_and_whitespace_collapse():
    assert normalize_text("\uff21\uff22\uff23  x\u00b2", NC) == "ABC x2"
    assert normalize_text("Hello   world\r\n\r\n\r\n\r\nline", NC) == "Hello world\n\nline"


def test_whitespace_only_record_is_removed_after_normalize():
    r = normalize([doc("a", "   \u200b  "), doc("b", "  Hi   there  ")], NC)
    assert r.reason_counts() == {"empty_after_normalize": 1}
    assert r.kept[0].text == "Hi there"