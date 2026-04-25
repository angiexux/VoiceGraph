"""Concept expansion tool — full neighborhood + cross-document + temporal analysis.

Triggered by: "what do I know about X?", "tell me about X in my notes",
"how does X connect to everything?"
"""

from __future__ import annotations

import logging
from typing import Any

from agents import context as ctx

logger = logging.getLogger(__name__)


async def concept_expand(concept: str) -> dict[str, Any]:
    """Expand a concept with full neighborhood, cross-document connections,
    and temporal evolution.

    Returns matching nodes, direct relationships grouped by type,
    cross-document connections, temporal evolution, and collections present in.
    """
    client = ctx.neo4j_client
    if client is None:
        return {"concept": concept, "error": "Neo4j not connected"}

    # Step 1: Find matching nodes
    exact_results = await client.execute_query(
        """
        MATCH (n)
        WHERE toLower(n.name) = toLower($name)
           OR toLower(n.name) CONTAINS toLower($name)
        RETURN n.name AS name, labels(n) AS types, elementId(n) AS id,
               n.description AS description
        LIMIT 5
        """,
        {"name": concept},
    )

    if not exact_results:
        return {
            "concept": concept,
            "matched_nodes": [],
            "direct_relationships": [],
            "cross_document_connections": [],
            "temporal_evolution": [],
            "collections_present_in": [],
            "message": f"No nodes found matching '{concept}'.",
        }

    # Step 2: 2-hop neighborhood
    neighborhood = await client.execute_query(
        """
        MATCH (center)-[r1]-(neighbor1)
        WHERE toLower(center.name) = toLower($name)
           OR toLower(center.name) CONTAINS toLower($name)
        WITH center, r1, neighbor1
        OPTIONAL MATCH (neighbor1)-[r2]-(neighbor2)
        WHERE neighbor2 <> center
        RETURN
            center.name AS concept,
            type(r1) AS rel_type,
            r1.description AS rel_description,
            neighbor1.name AS neighbor,
            labels(neighbor1) AS neighbor_types,
            neighbor1.source_document AS source_doc,
            neighbor1.collection_name AS collection,
            neighbor1.document_created_at AS doc_date,
            count(r2) AS neighbor_connections
        ORDER BY neighbor_connections DESC
        LIMIT 100
        """,
        {"name": concept},
    )

    # Step 3: Cross-document co-occurrence
    cross_doc = await client.execute_query(
        """
        MATCH (n)
        WHERE toLower(n.name) = toLower($name)
        WITH n
        MATCH (n)-[*1..2]-(other)
        WHERE other <> n
          AND n.collection_name IS NOT NULL
          AND other.collection_name IS NOT NULL
          AND n.collection_name <> other.collection_name
        RETURN DISTINCT
            other.name AS connected_concept,
            labels(other)[0] AS concept_type,
            n.collection_name AS in_collection_1,
            other.collection_name AS in_collection_2
        LIMIT 20
        """,
        {"name": concept},
    )

    # Step 4: Temporal evolution
    temporal = await client.execute_query(
        """
        MATCH (n)-[r]-(neighbor)
        WHERE toLower(n.name) = toLower($name)
          AND r.document_created_at IS NOT NULL
        RETURN
            type(r) AS relationship,
            neighbor.name AS with_concept,
            r.document_created_at AS when,
            r.source_document AS in_document
        ORDER BY when ASC
        LIMIT 50
        """,
        {"name": concept},
    )

    # Collect unique collections
    collections = set()
    for row in neighborhood:
        coll = row.get("collection")
        if coll:
            collections.add(coll)

    # Group relationships by type
    rel_groups: dict[str, list[str]] = {}
    for row in neighborhood:
        rt = row.get("rel_type", "RELATED_TO")
        nb = row.get("neighbor", "")
        if nb:
            rel_groups.setdefault(rt, []).append(nb)

    return {
        "concept": concept,
        "matched_nodes": exact_results,
        "direct_relationships": [
            {"type": k, "neighbors": v} for k, v in rel_groups.items()
        ],
        "cross_document_connections": cross_doc,
        "temporal_evolution": temporal,
        "collections_present_in": list(collections),
    }
