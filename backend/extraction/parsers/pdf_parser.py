"""PDF text extraction using PyPDF2 (pure Python, no system dependencies)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def parse_pdf(file_path: str) -> str:
    """Extract all text from a PDF file.

    Args:
        file_path: Absolute path to the PDF file.

    Returns:
        Concatenated text from all pages.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If PDF parsing fails.
    """
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise RuntimeError(
            "PyPDF2 is required for PDF parsing. Install with: pip install PyPDF2"
        )

    import os

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        reader = PdfReader(file_path)
        pages: list[str] = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append(text.strip())

        full_text = "\n\n".join(pages)
        logger.info(
            "Extracted %d characters from %d pages of %s",
            len(full_text),
            len(reader.pages),
            file_path,
        )
        return full_text

    except Exception as exc:
        raise RuntimeError(f"Failed to parse PDF '{file_path}': {exc}") from exc
