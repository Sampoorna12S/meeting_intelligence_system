import pytest

from meeting_ai.ingestion.parser import TranscriptParseError, parse_transcript


def test_bracket_format():
    turns = parse_transcript("[00:01:23] Alice: Hello there.\n[00:01:30] Bob: Hi!")
    assert [t.speaker for t in turns] == ["Alice", "Bob"]
    assert turns[0].seconds == 83 and turns[0].label == "00:01:23"
    assert turns[1].text == "Hi!"


def test_paren_format():
    turns = parse_transcript("Alice (00:01:23): Hello there.\nBob (00:02:00): Hi!")
    assert turns[0].speaker == "Alice" and turns[0].seconds == 83


def test_leading_timestamp_and_short_form():
    turns = parse_transcript("01:05 Alice: One\n1:10:00 Bob: Two")
    assert turns[0].seconds == 65 and turns[1].seconds == 4200 and turns[1].label == "01:10:00"


def test_plain_format_has_no_timestamps():
    turns = parse_transcript("Alice: Hello\nBob: Hi")
    assert turns[0].seconds is None and turns[0].label is None


def test_continuation_lines_and_preamble():
    text = "Weekly Sync\n\n[00:00:01] Alice: First line\nstill Alice talking\n[00:00:09] Bob: Reply"
    turns = parse_transcript(text)
    assert len(turns) == 2
    assert turns[0].text == "First line still Alice talking"


def test_windows_line_endings_and_bom():
    turns = parse_transcript("\ufeff[00:00:01] Alice: Hi\r\n[00:00:02] Bob: Yo\r\n")
    assert len(turns) == 2


def test_speaker_names_with_spaces():
    turns = parse_transcript("[00:00:01] Mary Jane: Hi")
    assert turns[0].speaker == "Mary Jane"


def test_rejects_unparseable():
    with pytest.raises(TranscriptParseError):
        parse_transcript("just some text without speakers at all")


def test_rejects_empty():
    with pytest.raises(TranscriptParseError):
        parse_transcript("   \n  ")
