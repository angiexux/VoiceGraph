"""API routes for Wiki Mode — list, get, and regenerate wiki pages."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from agents import context as ctx

router = APIRouter(prefix="/api/wiki", tags=["wiki"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_wiki_pages() -> dict[str, Any]:
    """List all wiki pages ordered by generation date (newest first)."""
    if ctx.neo4j_client is None or not ctx.neo4j_client.available:
        return {"pages": [], "count": 0}

    try:
        rows = await ctx.neo4j_client.execute_query(
            """
            MATCH (w:WikiPage)
            RETURN elementId(w) AS id, w.title AS title,
                   w.generated_at AS generated_at,
                   w.entity_count AS entity_count,
                   w.source_hint AS source_hint,
                   w.job_id AS job_id
            ORDER BY w.generated_at DESC
            LIMIT 100
            """
        )
        return {"pages": rows, "count": len(rows)}
    except Exception as exc:
        logger.error("Failed to list wiki pages: %s", exc)
        return {"pages": [], "count": 0}


@router.get("/{job_id}")
async def get_wiki_page(job_id: str) -> dict[str, Any]:
    """Get a single wiki page by job_id, including linked entity IDs for highlighting."""
    if ctx.neo4j_client is None or not ctx.neo4j_client.available:
        raise HTTPException(status_code=503, detail="Neo4j not connected")

    try:
        rows = await ctx.neo4j_client.execute_query(
            """
            MATCH (w:WikiPage {job_id: $job_id})
            OPTIONAL MATCH (w)-[:WIKI_COVERS]->(n:KGNode)
            RETURN w.title AS title, w.content_md AS content_md,
                   w.questions AS questions, w.generated_at AS generated_at,
                   w.entity_count AS entity_count,
                   collect(DISTINCT {id: elementId(n), name: n.name}) AS linked_entities
            """,
            {"job_id": job_id},
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Wiki page not found")

        row = rows[0]
        questions = row.get("questions", "[]")
        if isinstance(questions, str):
            try:
                questions = json.loads(questions)
            except Exception:
                questions = []

        return {
            "title": row.get("title", ""),
            "content_md": row.get("content_md", ""),
            "questions": questions,
            "generated_at": row.get("generated_at", ""),
            "entity_count": row.get("entity_count", 0),
            "linked_entities": [e for e in row.get("linked_entities", []) if e.get("name")],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get wiki page %s: %s", job_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/generate/{job_id}")
async def regenerate_wiki_page(job_id: str) -> dict[str, Any]:
    """Manually trigger wiki page re-generation for a job_id."""
    # For now: return a placeholder — full re-generation requires stored entities
    return {"message": f"Re-generation triggered for job {job_id}", "job_id": job_id}
