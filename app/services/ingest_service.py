import uuid
from typing import List, Tuple
from pypdf import PdfReader
from app.core.embeddings import embed_texts
from app.core.pinecone_client import get_index
from app.utils.logger import get_logger

logger = get_logger(__name__)

_CHUNK_SIZE = 500   # words per chunk
_CHUNK_OVERLAP = 50  # word overlap between chunks
_BATCH_SIZE = 100   # vectors per Pinecone upsert


def _extract_pages(file_path: str) -> List[Tuple[str, int]]:
    reader = PdfReader(file_path)
    pages = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text and text.strip():
            pages.append((text.strip(), page_num))
    return pages


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> List[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        chunk = " ".join(words[start : start + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def ingest_pdf(file_path: str, source_name: str) -> dict:
    logger.info(f"Ingesting PDF: {source_name}")
    pages = _extract_pages(file_path)
    if not pages:
        return {"status": "error", "message": "No extractable text found in PDF"}

    chunks, metadata = [], []
    for text, page_num in pages:
        for chunk in _chunk_text(text):
            chunks.append(chunk)
            metadata.append({"text": chunk, "source": source_name, "page": page_num})

    if not chunks:
        return {"status": "error", "message": "No chunks generated from PDF"}

    logger.info(f"Generated {len(chunks)} chunks from {len(pages)} pages")
    index = get_index()
    total = 0

    for i in range(0, len(chunks), _BATCH_SIZE):
        batch_chunks = chunks[i : i + _BATCH_SIZE]
        batch_meta = metadata[i : i + _BATCH_SIZE]
        embeddings = embed_texts(batch_chunks)
        vectors = [
            {"id": str(uuid.uuid4()), "values": emb, "metadata": meta}
            for emb, meta in zip(embeddings, batch_meta)
        ]
        index.upsert(vectors=vectors)
        total += len(vectors)
        logger.info(f"Upserted batch {i // _BATCH_SIZE + 1} ({len(vectors)} vectors)")

    return {"status": "success", "source": source_name, "pages": len(pages), "chunks": total}


def ingest_text(text: str, source_name: str) -> dict:
    chunks = _chunk_text(text)
    if not chunks:
        return {"status": "error", "message": "No chunks generated"}

    embeddings = embed_texts(chunks)
    vectors = [
        {
            "id": str(uuid.uuid4()),
            "values": emb,
            "metadata": {"text": chunk, "source": source_name},
        }
        for chunk, emb in zip(chunks, embeddings)
    ]
    get_index().upsert(vectors=vectors)
    return {"status": "success", "source": source_name, "chunks": len(vectors)}
