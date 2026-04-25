"""Document ingestion tools -- ingest PDFs, URLs, YouTube transcripts,
text files, and CSVs into the knowledge graph.

Each function is registered as an ADK tool. Docstrings serve as the
tool descriptions visible to the LLM.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from agents import context as ctx
from ingestion.job_manager import JobManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source type detection
# ---------------------------------------------------------------------------

_EXTENSION_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "text",
    ".csv": "csv",
    ".json": "text",
}


def _detect_source_type(source: str) -> str:
    """Auto-detect the source type from the source string."""
    lower = source.lower().strip()

    # YouTube
    if any(domain in lower for domain in ("youtube.com", "youtu.be")):
        return "youtube"

    # URL
    if lower.startswith(("http://", "https://")):
        return "url"

    # File extension
    _, ext = os.path.splitext(lower)
    return _EXTENSION_MAP.get(ext, "text")


# ---------------------------------------------------------------------------
# Module-level job manager for agent tool invocations
# ---------------------------------------------------------------------------

_job_manager: JobManager | None = None


def _get_job_manager() -> JobManager:
    """Lazily create a module-level JobManager."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


# ---------------------------------------------------------------------------
# Tool: ingest_document
# ---------------------------------------------------------------------------


def ingest_document(source: str, source_type: str = "auto") -> dict:
    """Ingest a document into the knowledge graph. Supports multiple formats:
    - PDF files (local path)
    - Web URLs (fetches and extracts text)
    - YouTube videos (extracts transcript)
    - Plain text or markdown files
    - CSV files (delegates to CSVAnalysisAgent for schema detection)

    source: file path or URL to ingest
    source_type: 'pdf', 'url', 'youtube', 'text', 'csv', or 'auto' (detect from source)"""

    if source_type == "auto":
        source_type = _detect_source_type(source)

    # Validate file exists for local paths
    if source_type in ("pdf", "text", "csv") and not source.startswith(("http://", "https://")):
        if not os.path.exists(source):
            return {
                "success": False,
                "source": source,
                "source_type": source_type,
                "message": f"File not found: {source}",
            }

    # Get shared resources from agent context
    neo4j_client = ctx.neo4j_client
    ontology_manager = ctx.ontology_manager
    broadcast_fn = ctx.ws_broadcast

    if broadcast_fn is None:
        # No WebSocket broadcast available -- provide a no-op
        async def _noop_broadcast(event: dict) -> None:
            pass
        broadcast_fn = _noop_broadcast

    job_manager = _get_job_manager()
    job = job_manager.create_job(source_type=source_type, source_preview=source[:200])

    # Run the ingestion asynchronously.
    # ADK tools are called synchronously, so we schedule the coroutine
    # on the running event loop.
    from ingestion.ingest import run_ingestion

    try:
        loop = asyncio.get_running_loop()
        # Schedule the async ingestion; don't await -- it runs in background
        future = asyncio.ensure_future(run_ingestion(
            job_id=job.id,
            source_type=source_type,
            content=source,
            job_manager=job_manager,
            neo4j_client=neo4j_client,
            ontology_manager=ontology_manager,
            broadcast_fn=broadcast_fn,
        ))

        return {
            "success": True,
            "source": source,
            "source_type": source_type,
            "job_id": job.id,
            "status": "started",
            "message": (
                f"Ingestion started for '{source}' (type: {source_type}). "
                f"Job ID: {job.id}. The extraction pipeline is running in the "
                f"background -- entities and relationships will be added to the "
                f"knowledge graph as they are discovered."
            ),
        }
    except RuntimeError:
        # No running event loop (e.g., called from sync context in tests)
        return {
            "success": True,
            "source": source,
            "source_type": source_type,
            "job_id": job.id,
            "status": "queued",
            "message": (
                f"Ingestion queued for '{source}' (type: {source_type}). "
                f"Job ID: {job.id}. Will be processed when the event loop is available."
            ),
        }
