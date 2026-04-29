"""Text embedding utility using Google's text-embedding-004 model."""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768


async def get_embedding(text: str) -> list[float] | None:
    """Embed *text* using text-embedding-004. Returns None when unavailable."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key or not text.strip():
        return None

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text[:3000],
            ),
        )
        return list(result.embeddings[0].values)
    except Exception as exc:
        logger.warning("Embedding failed: %s", exc)
        return None
