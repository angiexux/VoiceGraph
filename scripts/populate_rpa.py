#!/usr/bin/env python3
"""Pre-load Rockefeller Philanthropy Advisors public knowledge into VoiceGraph.

Crawls rockpa.org/publications and rockpa.org/resources, downloads all
public PDFs, and ingests them using the philanthropy ontology.

Usage:
    cd backend
    python ../scripts/populate_rpa.py

Environment vars required (same as backend/.env):
    GOOGLE_API_KEY, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

# Add backend to path so imports resolve when run from any directory
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RPA_BASE = "https://www.rockpa.org"
CRAWL_PAGES = [
    "/publications/",
    "/resources/",
    "/about/thought-leadership/",
]
MAX_PDFS = 50  # Cap to avoid overwhelming the graph on first run


def find_pdf_links(html: str, base_url: str) -> list[str]:
    """Extract PDF links from HTML."""
    import re

    hrefs = re.findall(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', html, re.IGNORECASE)
    links = []
    for href in hrefs:
        if href.startswith("http"):
            links.append(href)
        else:
            links.append(urljoin(base_url, href))
    return list(dict.fromkeys(links))  # Deduplicate preserving order


def crawl_page(url: str) -> tuple[str, list[str]]:
    """Fetch a page and return (html, pdf_links)."""
    import requests

    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "VoiceGraph/1.0"})
        resp.raise_for_status()
        html = resp.text
        pdfs = find_pdf_links(html, url)
        return html, pdfs
    except Exception as exc:
        logger.warning("Failed to crawl %s: %s", url, exc)
        return "", []


def download_pdf(url: str, dest_dir: str) -> str | None:
    """Download a PDF and return the local file path."""
    import requests

    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "VoiceGraph/1.0"})
        resp.raise_for_status()

        filename = urlparse(url).path.split("/")[-1] or "document.pdf"
        if not filename.endswith(".pdf"):
            filename += ".pdf"

        dest = os.path.join(dest_dir, filename)
        with open(dest, "wb") as f:
            f.write(resp.content)
        return dest
    except Exception as exc:
        logger.warning("Failed to download %s: %s", url, exc)
        return None


async def load_rpa_ontology() -> None:
    """Load the RPA philanthropy ontology into the extraction pipeline."""
    ontology_path = (
        Path(__file__).parent.parent / "backend" / "data" / "ontologies" / "rpa_ontology.ttl"
    )
    if not ontology_path.exists():
        logger.warning("RPA ontology file not found at %s", ontology_path)
        return

    try:
        from extraction.ontology_manager import OntologyManager

        mgr = OntologyManager()
        mgr.load_from_turtle(str(ontology_path))
        schema = mgr.to_graph_schema()
        logger.info(
            "RPA ontology loaded: %d classes, %d properties",
            len(schema["node_types"]),
            len(schema["relationship_types"]),
        )
    except Exception as exc:
        logger.warning("Failed to load RPA ontology: %s", exc)


async def ingest_pdf(pdf_path: str, neo4j_client: Any, file_name: str) -> None:
    """Ingest a single PDF into the knowledge graph."""
    from extraction.pipeline import ExtractionPipeline

    async def _log_event(event: dict) -> None:
        etype = event.get("type", "")
        if etype in ("phase_a_complete", "phase_c_complete", "pipeline_complete"):
            logger.info("[%s] %s", file_name, event.get("status", etype))

    pipeline = ExtractionPipeline(
        neo4j_client=neo4j_client,
        event_callback=_log_event,
        metadata={
            "source_type": "pdf",
            "collection_name": "rpa_publications",
            "context": "rockefeller_philanthropy_advisors",
        },
    )
    result = await pipeline.run(pdf_path, "pdf")
    if result.get("error"):
        logger.warning("Ingestion failed for %s: %s", file_name, result["error"])
    else:
        phase_c = result.get("phase_c") or {}
        logger.info(
            "  %s — %d entities, %d relationships",
            file_name,
            phase_c.get("total_entities", 0),
            phase_c.get("total_relationships", 0),
        )


async def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

    from graph.neo4j_client import Neo4jClient

    # Connect to Neo4j
    neo4j = Neo4jClient()
    await neo4j.connect()
    if not neo4j.available:
        logger.error("Neo4j not available — check NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD")
        return

    # Load RPA ontology
    await load_rpa_ontology()

    # Crawl RPA website for PDFs
    logger.info("Crawling rockpa.org for public publications...")
    all_pdfs: list[str] = []
    for page_path in CRAWL_PAGES:
        url = RPA_BASE + page_path
        logger.info("Crawling %s", url)
        _, pdfs = crawl_page(url)
        logger.info("  Found %d PDFs", len(pdfs))
        all_pdfs.extend(pdfs)

    # Deduplicate
    all_pdfs = list(dict.fromkeys(all_pdfs))
    logger.info("Total unique PDFs found: %d (capping at %d)", len(all_pdfs), MAX_PDFS)
    all_pdfs = all_pdfs[:MAX_PDFS]

    if not all_pdfs:
        logger.warning("No PDFs found. Check if rockpa.org structure has changed.")
        return

    # Download and ingest
    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, pdf_url in enumerate(all_pdfs, start=1):
            logger.info("[%d/%d] Processing: %s", i, len(all_pdfs), pdf_url)
            local_path = download_pdf(pdf_url, tmp_dir)
            if local_path:
                file_name = os.path.basename(local_path)
                await ingest_pdf(local_path, neo4j, file_name)
                time.sleep(1)  # Rate limit

    await neo4j.close()
    logger.info("RPA pre-load complete!")


if __name__ == "__main__":
    asyncio.run(main())
