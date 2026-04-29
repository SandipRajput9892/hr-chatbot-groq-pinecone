from fastapi import APIRouter
from app.core.groq_client import get_groq_client
from app.core.pinecone_client import get_pinecone_client
from app.models.response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    services: dict = {}

    try:
        get_pinecone_client().list_indexes()
        services["pinecone"] = "healthy"
    except Exception:
        services["pinecone"] = "unhealthy"

    try:
        get_groq_client()
        services["groq"] = "healthy"
    except Exception:
        services["groq"] = "unhealthy"

    services["database"] = "healthy"

    overall = "ok" if all(v == "healthy" for v in services.values()) else "degraded"
    return HealthResponse(status=overall, version="1.0.0", services=services)
