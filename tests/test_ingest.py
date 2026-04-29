"""Tests for ingest_service — no external services required."""
import pytest
from unittest.mock import MagicMock, patch


# ─── chunk_text ───────────────────────────────────────────────────────────────

def test_chunk_text_empty_string():
    from app.services.ingest_service import _chunk_text
    assert _chunk_text("") == []


def test_chunk_text_single_chunk():
    from app.services.ingest_service import _chunk_text
    text = " ".join(["word"] * 10)
    chunks = _chunk_text(text, chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_multiple_chunks():
    from app.services.ingest_service import _chunk_text
    text = " ".join(["word"] * 1100)
    chunks = _chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk.split()) <= 500


def test_chunk_text_overlap_creates_extra_chunk():
    from app.services.ingest_service import _chunk_text
    text = " ".join(["word"] * 600)
    chunks_no_overlap = _chunk_text(text, chunk_size=500, overlap=0)
    chunks_with_overlap = _chunk_text(text, chunk_size=500, overlap=100)
    assert len(chunks_with_overlap) >= len(chunks_no_overlap)


# ─── ingest_text ──────────────────────────────────────────────────────────────

def test_ingest_text_empty():
    from app.services.ingest_service import ingest_text
    with patch("app.services.ingest_service.get_index"), \
         patch("app.services.ingest_service.embed_texts", return_value=[]):
        result = ingest_text("", "empty_source")
    assert result["status"] == "error"


def test_ingest_text_calls_pinecone(monkeypatch):
    mock_index = MagicMock()
    dummy_embeddings = [[0.1] * 1024] * 3

    monkeypatch.setattr("app.services.ingest_service.get_index", lambda: mock_index)
    monkeypatch.setattr("app.services.ingest_service.embed_texts", lambda texts: dummy_embeddings[: len(texts)])

    from app.services.ingest_service import ingest_text

    result = ingest_text("This is a sample HR policy text. " * 50, "policy.txt")
    assert result["status"] == "success"
    assert mock_index.upsert.called
    assert result["chunks"] > 0
