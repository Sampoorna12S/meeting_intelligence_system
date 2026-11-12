from meeting_ai.ingestion.chunker import chunk_turns
from meeting_ai.ingestion.parser import parse_transcript


def _turns(n, speakers=("Alice", "Bob"), words=20):
    lines = []
    for i in range(n):
        lines.append(f"[00:{i // 60:02d}:{i % 60:02d}] {speakers[i % len(speakers)]}: " + " ".join(f"w{i}x{j}" for j in range(words)) + ".")
    return parse_transcript("\n".join(lines))


def test_single_chunk_for_short_transcript():
    chunks = chunk_turns(_turns(3))
    assert len(chunks) == 1
    assert chunks[0].speakers == ["Alice", "Bob"]
    assert chunks[0].start_label == "00:00:00"
    assert chunks[0].overlap_lines == 0


def test_multiple_chunks_overlap_and_cover_everything():
    turns = _turns(30)
    chunks = chunk_turns(turns, target_chars=400, overlap_turns=1)
    assert len(chunks) > 1
    assert all(len(c.text) <= 400 + 200 for c in chunks)
    assert chunks[0].overlap_lines == 0
    assert all(c.overlap_lines == 1 for c in chunks[1:])
    # last line of chunk k is the first line of chunk k+1
    for a, b in zip(chunks, chunks[1:]):
        assert a.text.split("\n")[-1] == b.text.split("\n")[0]
    # dropping the overlap lines reproduces every turn exactly once
    rebuilt = []
    for c in chunks:
        rebuilt.extend(c.text.split("\n")[c.overlap_lines :])
    assert len(rebuilt) == 30
    assert [i for i, _ in enumerate(rebuilt)] == list(range(30))


def test_adjacent_same_speaker_turns_are_merged():
    turns = parse_transcript("[00:00:01] Alice: One.\n[00:00:05] Alice: Two.\n[00:00:09] Bob: Three.")
    chunk = chunk_turns(turns)[0]
    lines = chunk.text.split("\n")
    assert len(lines) == 2
    assert lines[0] == "[00:00:01] Alice: One. Two."


def test_long_turn_is_split_on_sentences():
    sentence = "This is a fairly long sentence about the roadmap. "
    turns = parse_transcript("[00:00:01] Alice: " + sentence * 40 + "\n[00:00:50] Bob: Short reply.")
    chunks = chunk_turns(turns, target_chars=500)
    assert len(chunks) >= 3
    assert all(len(line) <= 600 for c in chunks for line in c.text.split("\n"))


def test_no_timestamps_gives_empty_labels():
    chunk = chunk_turns(parse_transcript("Alice: Hello\nBob: Hi"))[0]
    assert chunk.start_seconds == -1 and chunk.start_label == ""
    assert chunk.text.startswith("Alice: Hello")


def test_metadata_is_scalar():
    meta = chunk_turns(_turns(2))[0].metadata("s1")
    assert all(isinstance(v, (str, int, float, bool)) for v in meta.values())
    assert meta["session_id"] == "s1"
