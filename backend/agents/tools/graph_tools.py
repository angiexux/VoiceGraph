"""Graph UI tools — emit WebSocket events to control the frontend
3D force-graph visualization.

Each function is registered as an ADK tool. Docstrings serve as the
tool descriptions visible to the LLM.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from agents import context as ctx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper — broadcast a WebSocket event to all connected frontend clients
# ---------------------------------------------------------------------------


def _broadcast(event: dict) -> None:
    """Send an event via WebSocket broadcast. Falls back to logging if
    the broadcast function is not configured."""
    fn = ctx.ws_broadcast
    if fn is None:
        logger.info("ws_broadcast not set — event logged: %s", event.get("type"))
        return

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(fn(event))
    except RuntimeError:
        # No running event loop — run synchronously
        asyncio.run(fn(event))


# ---------------------------------------------------------------------------
# Helper — run Cypher
# ---------------------------------------------------------------------------


async def _run_cypher(cypher: str) -> list[dict]:
    client = ctx.neo4j_client
    if client is None:
        return []
    try:
        return await client.execute_query(cypher)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cypher execution failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Tool: highlight_nodes
# ---------------------------------------------------------------------------


async def highlight_nodes(node_ids: list[str], edge_ids: list[str] = []) -> dict:
    """Highlight specific nodes and edges in the graph visualization.
    Non-highlighted nodes dim to 20% opacity. Always call this after
    a query to visually show the user which parts of the graph are relevant.
    Accepts either Neo4j element IDs or entity names — names are resolved automatically."""

    resolved_ids = []
    client = ctx.neo4j_client

    for nid in node_ids:
        # If it looks like a Neo4j element ID (contains ':'), use as-is
        if ':' in nid:
            resolved_ids.append(nid)
        elif client is not None:
            # Resolve name to ID
            try:
                results = await client.execute_query(
                    "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($name) "
                    "RETURN elementId(n) AS id LIMIT 3",
                    {"name": nid},
                )
                for r in results:
                    resolved_ids.append(r["id"])
            except Exception:
                pass
        if not resolved_ids:
            resolved_ids.append(nid)  # fallback

    _broadcast({
        "type": "highlight",
        "nodeIds": resolved_ids + node_ids,  # Send both resolved IDs and original names
        "edgeIds": edge_ids,
    })

    return {
        "highlighted_nodes": len(resolved_ids),
        "highlighted_edges": len(edge_ids),
        "message": f"Highlighted {len(resolved_ids)} nodes and {len(edge_ids)} edges.",
    }


# ---------------------------------------------------------------------------
# Tool: expand_node
# ---------------------------------------------------------------------------


def expand_node(node_id: str) -> dict:
    """Expand a node to show its neighbors in the graph visualization.
    Loads neighbors from Neo4j and sends them to the frontend for rendering."""

    _broadcast({
        "type": "expand_node",
        "node_id": node_id,
    })

    return {
        "node_id": node_id,
        "message": f"Expand event sent for node '{node_id}'.",
    }


# ---------------------------------------------------------------------------
# Tool: dim_nodes
# ---------------------------------------------------------------------------


def dim_nodes() -> dict:
    """Clear all highlights and restore normal graph view.
    All nodes return to full opacity."""

    _broadcast({
        "type": "dim",
    })

    return {
        "message": "All highlights cleared. Graph restored to normal view.",
    }


# ---------------------------------------------------------------------------
# Tool: add_node
# ---------------------------------------------------------------------------


async def add_node(name: str, entity_type: str, description: str = "") -> dict:
    """Add a new entity to the knowledge graph and display it in the
    visualization. Creates the node in Neo4j and notifies the frontend."""

    client = ctx.neo4j_client
    node_id = None

    if client is not None:
        try:
            cypher = (
                f"CREATE (n:`{entity_type}` {{name: $name, description: $desc}}) "
                f"RETURN elementId(n) AS id"
            )
            results = await client.execute_query(cypher, {"name": name, "desc": description})
            if results:
                node_id = results[0].get("id")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to create node in Neo4j: %s", exc)

    _broadcast({
        "type": "node_added",
        "node": {
            "id": node_id or f"temp_{name}",
            "label": name,
            "type": entity_type,
            "properties": {"name": name, "entity_type": entity_type, "description": description},
        },
    })

    return {
        "node_id": node_id or f"temp_{name}",
        "name": name,
        "entity_type": entity_type,
        "created_in_neo4j": node_id is not None,
        "message": f"Created entity '{name}' of type '{entity_type}'.",
    }


# ---------------------------------------------------------------------------
# Tool: add_relationship
# ---------------------------------------------------------------------------


async def add_relationship(source_name: str, target_name: str, relationship_type: str) -> dict:
    """Add a new relationship between two existing entities in the knowledge
    graph. Connects them in Neo4j and updates the visualization."""

    client = ctx.neo4j_client
    created = False

    if client is not None:
        try:
            cypher = (
                "MATCH (a {name: $source}), (b {name: $target}) "
                f"CREATE (a)-[r:`{relationship_type}`]->(b) "
                "RETURN elementId(r) AS id"
            )
            results = await client.execute_query(cypher, {
                "source": source_name,
                "target": target_name,
            })
            created = bool(results)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to create relationship in Neo4j: %s", exc)

    # Find actual node IDs for source and target by name
    source_id = source_name
    target_id = target_name
    if client is not None:
        try:
            id_results = await client.execute_query(
                "MATCH (n) WHERE toLower(n.name) = toLower($name) RETURN elementId(n) AS id LIMIT 1",
                {"name": source_name},
            )
            if id_results:
                source_id = id_results[0]["id"]
            id_results = await client.execute_query(
                "MATCH (n) WHERE toLower(n.name) = toLower($name) RETURN elementId(n) AS id LIMIT 1",
                {"name": target_name},
            )
            if id_results:
                target_id = id_results[0]["id"]
        except Exception:
            pass

    _broadcast({
        "type": "edge_added",
        "edge": {
            "id": f"e-{source_name}-{relationship_type}-{target_name}",
            "source": source_id,
            "target": target_id,
            "label": relationship_type,
            "properties": {},
        },
    })

    return {
        "source": source_name,
        "target": target_name,
        "relationship_type": relationship_type,
        "created_in_neo4j": created,
        "message": f"Created relationship '{source_name}' --[{relationship_type}]--> '{target_name}'.",
    }


# ---------------------------------------------------------------------------
# Tool: remove_node
# ---------------------------------------------------------------------------


async def remove_node(name: str) -> dict:
    """Remove an entity from the knowledge graph by name.
    Deletes the node and all its relationships from Neo4j and updates
    the visualization."""

    client = ctx.neo4j_client
    deleted = False
    node_id = None

    if client is not None:
        try:
            # Find the node ID first
            id_results = await client.execute_query(
                "MATCH (n) WHERE toLower(n.name) = toLower($name) "
                "RETURN elementId(n) AS id LIMIT 1",
                {"name": name},
            )
            if id_results:
                node_id = id_results[0]["id"]
                # Delete the node and all its relationships
                await client.execute_query(
                    "MATCH (n) WHERE elementId(n) = $id DETACH DELETE n",
                    {"id": node_id},
                )
                deleted = True
        except Exception as exc:
            logger.warning("Failed to delete node in Neo4j: %s", exc)

    if node_id:
        _broadcast({
            "type": "node_removed",
            "nodeId": node_id,
        })

    return {
        "name": name,
        "node_id": node_id,
        "deleted_from_neo4j": deleted,
        "message": f"Deleted entity '{name}'." if deleted else f"Entity '{name}' not found.",
    }
