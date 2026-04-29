from typing import Any, Dict, List, Optional
from app.core.embeddings import embed_query
from app.core.pinecone_client import get_index
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MIN_SCORE          = 0.30   # threshold for unfiltered (all-docs) queries
_MIN_SCORE_FILTERED = 0.10   # lower threshold when user pins a specific document


def check_source_indexed(source: str) -> bool:
    """Return True if Pinecone has at least one vector with this source name."""
    try:
        vector = embed_query(source)
        results = get_index().query(
            vector=vector,
            top_k=1,
            include_metadata=False,
            filter={"source": {"$eq": source}},
        )
        return len(results.matches) > 0
    except Exception:
        return False


def retrieve_relevant_context(
    query: str,
    top_k: int = 5,
    source_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    try:
        vector = embed_query(query)
        kwargs: Dict[str, Any] = dict(vector=vector, top_k=top_k, include_metadata=True)
        if source_filter:
            kwargs["filter"] = {"source": {"$eq": source_filter}}
        results = get_index().query(**kwargs)
        min_score = _MIN_SCORE_FILTERED if source_filter else _MIN_SCORE
        return [
            {
                "id": m.id,
                "score": round(m.score, 4),
                "text": m.metadata.get("text", ""),
                "source": m.metadata.get("source", "unknown"),
                "page": m.metadata.get("page"),
            }
            for m in results.matches
            if m.score >= min_score
        ]
    except Exception as exc:
        logger.error(f"Retrieval error: {exc}")
        return []


def format_context(matches: List[Dict[str, Any]]) -> str:
    if not matches:
        return ""
    parts = []
    for m in matches:
        header = f"[Source: {m['source']}"
        if m.get("page"):
            header += f", Page {m['page']}"
        header += f" | Score: {m['score']}]"
        parts.append(f"{header}\n{m['text']}")
    return "\n\n---\n\n".join(parts)
