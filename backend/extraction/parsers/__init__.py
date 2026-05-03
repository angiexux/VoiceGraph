"""Multimodal document parsers for VoiceGraph.

Routes to the correct parser based on source type and returns clean text.
"""

from __future__ import annotations

import logging
import os

from .pdf_parser import parse_pdf
from .url_parser import parse_url
from .youtube_parser import parse_youtube
from .text_parser import parse_text
from .docx_parser import parse_docx
from .xlsx_parser import parse_xlsx
from .pptx_parser import parse_pptx
from .image_parser import parse_image, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

PARSER_MAP = {
    "pdf": parse_pdf,
    "url": parse_url,
    "youtube": parse_youtube,
    "text": parse_text,
    "markdown": parse_text,
    "docx": parse_docx,
    "xlsx": parse_xlsx,
    "pptx": parse_pptx,
    "image": parse_image,
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

    if source_type in ("folder", "zip"):
        raise ValueError(
            "ZIP/folder ingestion is not wired yet. Please extract files and upload PDF, DOCX, or TXT."
        )
    if source_type == "audio":
        raise ValueError(
            "Audio transcription is not configured. Paste a transcript or upload a text/PDF file."
        )

    # Auto-detect from source string if type is "auto"
    if source_type == "auto":
        if source.endswith(".pdf"):
            source_type = "pdf"
        elif "youtube.com" in source or "youtu.be" in source:
            source_type = "youtube"
        elif source.startswith("http://") or source.startswith("https://"):
            source_type = "url"
        elif source.lower().endswith(".docx"):
            source_type = "docx"
        elif source.lower().endswith((".xlsx", ".xls")):
            source_type = "xlsx"
        elif source.lower().endswith(".pptx"):
            source_type = "pptx"
        elif any(source.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            source_type = "image"
        else:
            source_type = "text"

    parser = PARSER_MAP.get(source_type)
    if parser is None:
        raise ValueError(
            f"Unknown source_type '{source_type}'. "
            f"Supported types: {', '.join(PARSER_MAP)}"
        )

    # REST file uploads pass a filesystem path; plain-text parser expects content, not a path.
    parse_arg = source
    if parser is parse_text and os.path.isfile(source):
        try:
            with open(source, encoding="utf-8", errors="replace") as fh:
                parse_arg = fh.read()
        except OSError as exc:
            raise ValueError(f"Could not read text file: {exc}") from exc

    logger.info("Parsing document with %s parser", source_type)
    return await parser(parse_arg)
