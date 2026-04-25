"""Folder/ZIP parser for Second Brain imports.

Extracts a ZIP file and routes each file to the appropriate parser.
Parses [[wikilinks]] in .md files as explicit high-confidence edges.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Wikilink patterns
WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]*)?\|?([^\]]*)\]\]')


def _parse_wikilinks(text: str) -> list[dict[str, str]]:
    """Extract [[wikilinks]] from markdown text.

    Handles:
      - [[simple link]]
      - [[note|display text]]
      - [[note#section]]
      - [[note#section|display]]

    Returns list of {target, display} dicts.
    """
    links = []
    for match in WIKILINK_RE.finditer(text):
        target = match.group(1).strip()
        display = match.group(2).strip() if match.group(2) else target
        if target:
            links.append({"target": target, "display": display})
    return links


async def parse_folder(zip_path: str) -> dict[str, Any]:
    """Extract ZIP and parse all supported files.

    Returns:
        {
            "chunks": [...],  # list of text chunks with metadata
            "wikilink_edges": [...],  # explicit edges from [[wikilinks]]
            "file_count": int,
            "skipped_files": [...]
        }
    """
    chunks: list[dict[str, Any]] = []
    wikilink_edges: list[dict[str, Any]] = []
    skipped_files: list[str] = []
    file_count = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmpdir)

        for root, _dirs, files in os.walk(tmpdir):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, tmpdir)
                ext = Path(fname).suffix.lower()

                # Get file mtime as document_created_at
                try:
                    mtime = os.path.getmtime(fpath)
                    doc_created = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
                except Exception:
                    doc_created = datetime.now(timezone.utc).isoformat()

                base_meta = {
                    "source_type": "folder",
                    "source_file": fname,
                    "folder_path": rel_path,
                    "document_created_at": doc_created,
                }

                try:
                    if ext == '.pdf':
                        from extraction.parsers.pdf_parser import parse_pdf
                        text = await parse_pdf(fpath)
                        chunks.append({"text": text, **base_meta})
                        file_count += 1

                    elif ext in ('.txt', '.md'):
                        from extraction.parsers.text_parser import parse_text
                        text = await parse_text(fpath)
                        chunks.append({"text": text, **base_meta})
                        file_count += 1

                        # Parse wikilinks from markdown
                        if ext == '.md':
                            links = _parse_wikilinks(text)
                            source_name = Path(fname).stem
                            for link in links:
                                wikilink_edges.append({
                                    "source": source_name,
                                    "target": link["target"],
                                    "type": "REFERENCED_IN",
                                    "confidence": 0.95,
                                    "source_file": fname,
                                    "folder_path": rel_path,
                                })

                    elif ext == '.csv':
                        with open(fpath, 'r', errors='replace') as f:
                            text = f.read()
                        chunks.append({"text": text, **base_meta, "source_type": "csv"})
                        file_count += 1

                    elif ext in ('.mp3', '.wav', '.m4a', '.mp4'):
                        try:
                            from ingestion.parsers.audio_parser import parse_audio
                            audio_chunks = await parse_audio(fpath)
                            for ac in audio_chunks:
                                ac.update(base_meta)
                                ac["source_type"] = "audio"
                            chunks.extend(audio_chunks)
                            file_count += 1
                        except Exception as exc:
                            logger.warning("Audio parse failed for %s: %s", fname, exc)
                            skipped_files.append(f"{rel_path} (audio error: {exc})")

                    elif ext == '.docx':
                        try:
                            from docx import Document
                            doc = Document(fpath)
                            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                            chunks.append({"text": text, **base_meta})
                            file_count += 1
                        except ImportError:
                            logger.warning("python-docx not installed, skipping %s", fname)
                            skipped_files.append(f"{rel_path} (python-docx not installed)")

                    elif ext in ('.html', '.htm'):
                        try:
                            from bs4 import BeautifulSoup
                            with open(fpath, 'r', errors='replace') as f:
                                soup = BeautifulSoup(f.read(), 'html.parser')
                            text = soup.get_text(separator='\n', strip=True)
                            chunks.append({"text": text, **base_meta})
                            file_count += 1
                        except ImportError:
                            logger.warning("beautifulsoup4 not installed, skipping %s", fname)
                            skipped_files.append(f"{rel_path} (beautifulsoup4 not installed)")

                    else:
                        skipped_files.append(f"{rel_path} (unsupported extension: {ext})")

                except Exception as exc:
                    logger.warning("Failed to parse %s: %s", rel_path, exc)
                    skipped_files.append(f"{rel_path} (error: {exc})")

    logger.info("Parsed %d files from ZIP, %d skipped", file_count, len(skipped_files))
    return {
        "chunks": chunks,
        "wikilink_edges": wikilink_edges,
        "file_count": file_count,
        "skipped_files": skipped_files,
    }
