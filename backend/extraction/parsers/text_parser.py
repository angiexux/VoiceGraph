"""Plain text / markdown passthrough parser with basic cleaning."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


async def parse_text(content: str) -> str:
    """Clean and return plain text or markdown content.

    Performs basic cleaning:
      - Strips leading/trailing whitespace
      - Normalises line endings
      - Collapses excessive blank lines

    Args:
        content: Raw text or markdown content.

    Returns:
        Cleaned text.
    """
    if not content:
        return ""

    # Normalise line endings
    text = content.replace("\r\n", "\n").replace("\r", "\n")

    # Strip leading/trailing whitespace
    text = text.strip()

    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    logger.info("Text parser: %d characters", len(text))
    return text
