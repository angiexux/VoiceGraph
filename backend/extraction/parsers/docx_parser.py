"""Word document (.docx) parser using python-docx."""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def parse_docx(source: str) -> str:
    """Extract text from a .docx file path.

    Extracts paragraph text and table cell text in reading order.
    """
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx not installed. Run: pip install python-docx")
        return ""

    try:
        doc = Document(source)
        parts: list[str] = []

        for block in doc.element.body:
            tag = block.tag.split("}")[-1] if "}" in block.tag else block.tag

            if tag == "p":
                # Paragraph
                from docx.oxml.ns import qn
                text = "".join(
                    node.text for node in block.iter(qn("w:t")) if node.text
                )
                if text.strip():
                    parts.append(text.strip())

            elif tag == "tbl":
                # Table — flatten cells row by row
                from docx.oxml.ns import qn
                for row in block.iter(qn("w:tr")):
                    cells = []
                    for cell in row.iter(qn("w:tc")):
                        cell_text = " ".join(
                            t.text for t in cell.iter(qn("w:t")) if t.text
                        ).strip()
                        if cell_text:
                            cells.append(cell_text)
                    if cells:
                        parts.append(" | ".join(cells))

        return "\n\n".join(parts)

    except Exception as exc:
        logger.error("Failed to parse docx '%s': %s", source, exc)
        return ""
