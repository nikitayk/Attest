"""Deterministic chunking — Step 1.2."""

from app.ingest import chunk_text


def test_chunk_text_is_deterministic():
    """Same input must always produce identical chunks — required for re-ingest hash stability."""
    text = "abcdefghijklmnopqrstuvwxyz" * 40  # 1040 chars → multiple chunks at size 500
    first = chunk_text(text, chunk_size=500, overlap=50)
    second = chunk_text(text, chunk_size=500, overlap=50)

    assert first == second
    assert len(first) > 1
    assert all(len(c) <= 500 for c in first)


def test_chunk_text_normalizes_newlines_and_bom():
    """CRLF and BOM normalization must not change chunk boundaries vs clean LF input."""
    base = "line one\nline two\nline three\n"
    with_crlf = "line one\r\nline two\r\nline three\r\n"
    with_bom = "\ufeff" + base

    assert chunk_text(base, 500, 50) == chunk_text(with_crlf, 500, 50)
    assert chunk_text(base, 500, 50) == chunk_text(with_bom, 500, 50)


def test_chunk_text_empty_returns_empty_list():
    """Truly empty input yields no chunks."""
    assert chunk_text("", 500, 50) == []
    assert chunk_text("\ufeff", 500, 50) == []


def test_chunk_text_overlap_preserves_boundary_context():
    """Overlapping windows must repeat tail context across consecutive chunks."""
    text = "A" * 600
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    assert len(chunks) == 2
    assert chunks[0] == "A" * 500
    assert chunks[1] == "A" * 150  # 50-char overlap + remainder
