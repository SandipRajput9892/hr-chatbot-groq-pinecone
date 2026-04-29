from pinecone import Pinecone, ServerlessSpec
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_pc: Pinecone = None
_index = None


def get_pinecone_client() -> Pinecone:
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return _pc


def get_index():
    global _index
    if _index is None:
        _index = get_pinecone_client().Index(settings.PINECONE_INDEX_NAME)
    return _index


def init_pinecone_index() -> None:
    try:
        pc = get_pinecone_client()
        existing = [idx.name for idx in pc.list_indexes()]
        if settings.PINECONE_INDEX_NAME not in existing:
            logger.info(f"Creating Pinecone index '{settings.PINECONE_INDEX_NAME}' ...")
            pc.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=settings.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=settings.PINECONE_CLOUD,
                    region=settings.PINECONE_ENVIRONMENT,
                ),
            )
            logger.info("Pinecone index created.")
        else:
            logger.info(f"Pinecone index '{settings.PINECONE_INDEX_NAME}' already exists.")
    except Exception as exc:
        logger.warning(
            f"Could not connect to Pinecone during startup: {exc}. "
            "Chat/upload features will fail until Pinecone is reachable."
        )
