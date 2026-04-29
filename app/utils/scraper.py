from typing import Optional
import requests
from bs4 import BeautifulSoup
from app.utils.logger import get_logger

logger = get_logger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HRBot/1.0; +https://company.com)"}


def scrape_url(url: str, timeout: int = 10) -> Optional[str]:
    try:
        response = requests.get(url, headers=_HEADERS, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as exc:
        logger.error(f"Scraping failed for {url}: {exc}")
        return None
