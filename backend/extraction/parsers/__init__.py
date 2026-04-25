"""Multimodal document parsers for VoiceGraph.

Routes to the correct parser based on source type and returns clean text.
"""

from __future__ import annotations

import logging

from .pdf_parser import parse_pdf
from .url_parser import parse_url
from .youtube_parser import parse_youtube
from .text_parser import parse_text

logger = logging.getLogger(__name__)

PARSER_MAP = {
    "pdf": parse_pdf,
    "url": parse_url,
    "youtube": parse_youtube,
    "text": parse_text,
    "markdown": parse_text,
}


async def parse_document(source: str, source_type: str) -> str:
    """Route to the appropriate parser based on *source_type*.

    Args:
        source: File path, URL, or raw text depending on type.
        source_type: One of ``pdf``, ``url``, ``youtube``, ``text``, ``markdown``.

    Returns:
        Cleaned plain text extracted from the source.

    Raises:
        ValueError: If *source_type* is not recognised.
    """
    source_type = source_type.lower().strip()

    # Auto-detect from source string if type is "auto"
    if source_type == "auto":
        if source.endswith(".pdf"):
            source_type = "pdf"
        elif "youtube.com" in source or "youtu.be" in source:
            source_type = "youtube"
        elif source.startswith("http://") or source.startswith("https://"):
            source_type = "url"
        else:
            source_type = "text"

    parser = PARSER_MAP.get(source_type)
    if parser is None:
        raise ValueError(
            f"Unknown source_type '{source_type}'. "
            f"Supported types: {', '.join(PARSER_MAP)}"
        )

    logger.info("Parsing document with %s parser", source_type)
    return await parser(source)
