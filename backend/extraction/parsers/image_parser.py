"""Image OCR parser using Gemini multimodal vision (no extra dependencies)."""

from __future__ import annotations
import asyncio
import base64
import logging
import os

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".tif", ".bmp"}


async def parse_image(source: str) -> str:
    """Extract text from an image file using Gemini vision.

    Works with PNG, JPEG, GIF, WebP, TIFF, BMP.
    Falls back to empty string if no API key or vision fails.
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("No Gemini API key — image OCR unavailable.")
        return ""

    try:
        with open(source, "rb") as f:
            image_bytes = f.read()
    except Exception as exc:
        logger.error("Cannot read image file '%s': %s", source, exc)
        return ""

    ext = os.path.splitext(source)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp", ".tiff": "image/tiff", ".tif": "image/tiff",
        ".bmp": "image/bmp",
    }
    mime_type = mime_map.get(ext, "image/png")
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "Extract ALL text from this image exactly as written. "
        "Include headings, body text, captions, labels, and table contents. "
        "Preserve the logical reading order. Output plain text only."
    )

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    {"role": "user", "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": b64}},
                        {"text": prompt},
                    ]},
                ],
            ),
        )
        return response.text.strip()

    except Exception as exc:
        logger.warning("Gemini image OCR failed for '%s': %s", source, exc)
        return ""
