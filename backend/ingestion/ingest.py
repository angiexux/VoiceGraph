"""Core ingestion orchestration.

Ties together the extraction pipeline, Neo4j storage,
and WebSocket event broadcasting.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Awaitable

from extraction.pipeline import ExtractionPipeline
from ingestion.job_manager import JobManager

logger = logging.getLogger(__name__)

BroadcastFn = Callable[[dict[str, Any]], Awaitable[None]]


def _normalize_ingest_node(n: dict[str, Any]) -> dict[str, Any]:
    """Convert a Neo4j-style node dict to frontend GraphNode format."""
    if "label" in n:
        return n
    labels_list = n.get("labels", [])
    props = n.get("properties", {})
    node_type = labels_list[0] if labels_list else "Concept"
    label = props.get("name") or props.get("label") or props.get("title")
    if not label:
        snippet = props.get("snippet") or props.get("summary") or props.get("description")
        if snippet:
            label = snippet[:50] + ("..." if len(snippet) > 50 else "")
        elif props.get("order_id"):
            side = props.get("side", "")
            label = f"{side} {props['order_id']}".strip()
        else:
            label = node_type
    return {
        "id": n["id"],
        "label": label,
        "type": node_type,
        "properties": props,
    }


def _normalize_ingest_edge(e: dict[str, Any]) -> dict[str, Any]:
    """Convert a Neo4j-style edge dict to frontend GraphEdge format."""
    if "label" in e:
        return e
    return {
        "id": e["id"],
        "source": e["source"],
        "target": e["target"],
        "label": e.get("type", "related_to").lower(),
        "properties": e.get("properties", {}),
    }


async def run_ingestion(
    job_id: str,
    source_type: str,
    content: str,
    job_manager: JobManager,
    neo4j_client: Any,
    ontology_manager: Any,
    broadcast_fn: BroadcastFn,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute ingestion: extract entities with Gemini → store in Neo4j → broadcast updates."""

    async def _broadcast_status(status: str, progress: float = 0.0, **extra: Any) -> None:
        job_manager.update_job(job_id, status=status, progress=progress)
        await broadcast_fn({
            "type": "ingestion_status",
            "job_id": job_id,
            "status": status,
            "progress": progress,
            **extra,
        })

    try:
        await _broadcast_status("parsing", 0.05)

        # Track live counts
        live_entities: list[str] = []
        live_relationships: list[str] = []

        # Pipeline event callback — forward progress to frontend
        async def pipeline_event_callback(event: dict[str, Any]) -> None:
            etype = event.get("type", "")

            status_map = {
                "phase_a_start": ("extracting", 0.10),
                "phase_a_progress": ("extracting", None),
                "phase_a_complete": ("extracting", 0.70),
                "phase_c_start": ("storing", 0.75),
                "phase_c_complete": ("storing", 0.90),
            }

            if etype in status_map:
                mapped_status, mapped_progress = status_map[etype]
                if mapped_progress is None:
                    sub = event.get("progress", 0.0)
                    mapped_progress = 0.10 + sub * 0.60
                job_manager.update_job(job_id, status=mapped_status, progress=mapped_progress)

                # Include chunk/total info for granular progress
                chunk_info = {}
                if "chunk" in event and "total_chunks" in event:
                    chunk_info = {"chunk": event["chunk"], "total_chunks": event["total_chunks"]}

                await broadcast_fn({
                    "type": "ingestion_status",
                    "job_id": job_id,
                    "status": mapped_status,
                    "phase": etype.replace("phase_", "").split("_")[0].upper(),
                    "progress": mapped_progress,
                    "detail": event.get("status", ""),
                    "entities_found": len(live_entities),
                    "relationships_found": len(live_relationships),
                    **chunk_info,
                })

            # Forward discovered entities as live node_added events
            if etype in ("entity_discovered", "node_added"):
                entity = event.get("entity", {})
                if entity:
                    name = entity.get("name", "")
                    etype_val = entity.get("type", "Entity")
                    live_entities.append(name)
                    node_data = {
                        "id": f"{etype_val.lower()}-{name.lower().replace(' ', '_')}",
                        "label": name,
                        "type": etype_val,
                        "properties": {
                            "name": name,
                            "entity_type": etype_val,
                            "description": entity.get("description", ""),
                        },
                    }
                    await broadcast_fn({
                        "type": "node_added",
                        "node": node_data,
                    })
                    # Also send count update so UI stays in sync
                    await broadcast_fn({
                        "type": "ingestion_status",
                        "job_id": job_id,
                        "status": "extracting",
                        "progress": 0.10 + (len(live_entities) * 0.5) % 60 * 0.01,
                        "entities_found": len(live_entities),
                        "relationships_found": len(live_relationships),
                        "latest_entity": name,
                        "latest_type": etype_val,
                    })

            # Track relationships too
            if etype == "relationship_discovered":
                rel = event.get("relationship", {})
                if rel:
                    live_relationships.append(rel.get("type", ""))

            # Reactive graph refresh — fetch real data from Neo4j and push to frontend
            if etype == "graph_refresh" and neo4j_client is not None:
                try:
                    graph = await neo4j_client.get_full_graph()
                    nodes = [_normalize_ingest_node(n) for n in graph.get("nodes", [])]
                    edges = [_normalize_ingest_edge(e) for e in graph.get("edges", [])]
                    await broadcast_fn({
                        "type": "graph_update",
                        "nodes": nodes,
                        "edges": edges,
                    })
                except Exception as exc:
                    logger.warning("graph_refresh failed: %s", exc)

        pipeline_neo4j = neo4j_client if (neo4j_client and neo4j_client.available) else None
        pipeline = ExtractionPipeline(
            neo4j_client=pipeline_neo4j,
            event_callback=pipeline_event_callback,
            metadata=metadata or {"source_type": source_type},
        )

        result = await pipeline.run(content, source_type)

        if result.get("error"):
            await _broadcast_status("error", 0.0, error=result["error"])
            job_manager.update_job(job_id, status="error", error=result["error"])
            return result

        phase_c = result.get("phase_c") or {}
        entities_found = phase_c.get("total_entities", 0)
        rels_found = phase_c.get("total_relationships", 0)

        # Send full graph refresh so frontend gets all nodes + edges
        if neo4j_client is not None:
            graph = await neo4j_client.get_full_graph()
            nodes = [_normalize_ingest_node(n) for n in graph.get("nodes", [])]
            edges = [_normalize_ingest_edge(e) for e in graph.get("edges", [])]
            await broadcast_fn({
                "type": "graph_update",
                "nodes": nodes,
                "edges": edges,
            })

        # Mark complete
        job_manager.update_job(
            job_id, status="complete", progress=1.0,
            entities_found=entities_found, relationships_found=rels_found,
        )
        await broadcast_fn({
            "type": "ingestion_status",
            "job_id": job_id,
            "status": "complete",
            "progress": 1.0,
            "entities_found": entities_found,
            "relationships_found": rels_found,
        })

        return result

    except Exception as exc:
        logger.error("Ingestion job %s failed: %s", job_id, exc, exc_info=True)
        job_manager.update_job(job_id, status="error", error=str(exc))
        await broadcast_fn({
            "type": "ingestion_status",
            "job_id": job_id,
            "status": "error",
            "progress": 0.0,
            "error": str(exc),
        })
        return {"error": str(exc)}
