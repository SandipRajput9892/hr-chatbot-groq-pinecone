"""Tests for chat pipeline — no external services required."""
import pytest
from unittest.mock import MagicMock, patch


# ─── retrieval_service ────────────────────────────────────────────────────────

def test_format_context_empty():
    from app.services.retrieval_service import format_context
    assert format_context([]) == ""


def test_format_context_includes_text_and_source():
    from app.services.retrieval_service import format_context
    matches = [
        {"id": "1", "score": 0.92, "text": "Employees are entitled to 20 days annual leave.", "source": "leave_policy.pdf", "page": 3},
    ]
    result = format_context(matches)
    assert "leave_policy.pdf" in result
    assert "20 days annual leave" in result
    assert "Page 3" in result


def test_format_context_multiple_sources():
    from app.services.retrieval_service import format_context
    matches = [
        {"id": "1", "score": 0.90, "text": "Text A", "source": "doc1.pdf", "page": 1},
        {"id": "2", "score": 0.85, "text": "Text B", "source": "doc2.pdf", "page": None},
    ]
    result = format_context(matches)
    assert "doc1.pdf" in result
    assert "doc2.pdf" in result
    assert "---" in result  # separator


def test_retrieve_returns_empty_on_error(monkeypatch):
    monkeypatch.setattr("app.services.retrieval_service.embed_query", MagicMock(side_effect=RuntimeError("network")))
    from app.services.retrieval_service import retrieve_relevant_context
    result = retrieve_relevant_context("test query")
    assert result == []


# ─── chat_service ─────────────────────────────────────────────────────────────

def test_chat_with_hr_saves_history(monkeypatch):
    mock_db = MagicMock()
    mock_employee = MagicMock()
    mock_employee.id = "emp-uuid"

    monkeypatch.setattr(
        "app.services.chat_service.retrieve_relevant_context",
        lambda q, top_k=5: [],
    )
    monkeypatch.setattr(
        "app.services.chat_service.generate_response",
        lambda messages, **kw: "You have 20 days of annual leave.",
    )
    # Simulate empty chat history query
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    from app.services.chat_service import chat_with_hr

    result = chat_with_hr(mock_db, mock_employee, "How much leave do I have?")

    assert "20 days" in result["message"]
    assert isinstance(result["sources"], list)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
