from typing import List
from groq import Groq
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client: Groq = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def generate_response(
    messages: List[dict],
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    client = get_groq_client()
    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content
