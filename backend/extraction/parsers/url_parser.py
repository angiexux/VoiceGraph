"""Web page scraping and text extraction."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


async def parse_url(url: str) -> str:
    """Scrape a web page and return cleaned plain text.

    Args:
        url: The URL to fetch.

    Returns:
        Cleaned text content of the page.

    Raises:
        RuntimeError: If fetching or parsing fails.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError(
            "requests and beautifulsoup4 are required for URL parsing. "
            "Install with: pip install requests beautifulsoup4"
        )

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script, style, nav, footer, header elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        # Get text
        text = soup.get_text(separator="\n")

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]  # remove blank lines
        text = "\n".join(lines)

        # Collapse runs of whitespace within lines
        text = re.sub(r"[ \t]+", " ", text)

        # Collapse 3+ consecutive newlines into 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        logger.info("Extracted %d characters from %s", len(text), url)
        return text

    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch URL '{url}': {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to parse URL '{url}': {exc}") from exc
