from typing import List

from app.config import settings
from app.core.pinecone_client import get_pinecone_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def embed_texts(texts: List[str]) -> List[List[float]]:
    pc = get_pinecone_client()
    response = pc.inference.embed(
        model=settings.EMBEDDING_MODEL,
        inputs=texts,
        parameters={"input_type": "passage", "truncate": "END"},
    )
    return [item["values"] for item in response]


def embed_query(text: str) -> List[float]:
    pc = get_pinecone_client()
    response = pc.inference.embed(
        model=settings.EMBEDDING_MODEL,
        inputs=[text],
        parameters={"input_type": "query", "truncate": "END"},
    )
    return response[0]["values"]
