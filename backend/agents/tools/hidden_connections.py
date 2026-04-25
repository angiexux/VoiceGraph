"""Hidden connections tool — find cross-document bridges and temporal co-occurrence.

MODE A: Concepts appearing in multiple collections act as bridges.
MODE B: Concepts consistently appearing together within 30-day windows.
"""

from __future__ import annotations

import logging
from typing import Any

from agents import context as ctx

logger = logging.getLogger(__name__)


async def cross_document_bridges() -> dict[str, Any]:
    """Find concepts that bridge multiple collections.

    These are nodes that appear in 2+ different collections,
    acting as conceptual bridges across the user's knowledge.
    """
    client = ctx.neo4j_client
    if client is None:
        return {"bridges": [], "error": "Neo4j not connected"}

    results = await client.execute_query(
        """
        MATCH (n)
        WHERE n.collection_name IS NOT NULL
        WITH n, n.collection_name AS coll
        WITH n, collect(DISTINCT coll) AS collections
        WHERE size(collections) >= 2
        RETURN n.name AS name, labels(n)[0] AS type,
               collections, size(collections) AS span
        ORDER BY span DESC
        LIMIT 20
        """
    )

    # Fallback: try using edges between nodes in different collections
    if not results:
        results = await client.execute_query(
            """
            MATCH (a)-[r]-(b)
            WHERE a.collection_name IS NOT NULL
              AND b.collection_name IS NOT NULL
              AND a.collection_name <> b.collection_name
            RETURN DISTINCT a.name AS name, labels(a)[0] AS type,
                   collect(DISTINCT a.collection_name) + collect(DISTINCT b.collection_name) AS collections,
                   2 AS span
            LIMIT 20
            """
        )

    return {
        "mode": "cross_document_bridges",
        "bridges": results,
        "count": len(results),
    }


async def temporal_cooccurrence() -> dict[str, Any]:
    """Find concepts that consistently appear together within 30-day windows.

    Detects patterns in the user's thinking — concepts they
    repeatedly explore in the same time frame.
    """
    client = ctx.neo4j_client
    if client is None:
        return {"patterns": [], "error": "Neo4j not connected"}

    results = await client.execute_query(
        """
        MATCH (a), (b)
        WHERE a <> b AND id(a) < id(b)
          AND a.document_created_at IS NOT NULL
          AND b.document_created_at IS NOT NULL
          AND a.collection_name IS NOT NULL
          AND b.collection_name IS NOT NULL
        WITH a, b,
             abs(duration.between(
                 date(a.document_created_at),
                 date(b.document_created_at)).days) AS day_diff
        WHERE day_diff <= 30
        WITH a.name AS concept_a, b.name AS concept_b,
             count(*) AS co_occurrences
        WHERE co_occurrences >= 2
        RETURN concept_a, concept_b, co_occurrences
        ORDER BY co_occurrences DESC
        LIMIT 15
        """
    )

    return {
        "mode": "temporal_cooccurrence",
        "patterns": results,
        "count": len(results),
    }


async def find_hidden_connections(mode: str = "bridges") -> dict[str, Any]:
    """Router for hidden connections analysis.

    mode='bridges': cross-document bridge concepts
    mode='temporal': temporal co-occurrence patterns
    """
    if mode == "temporal":
        return await temporal_cooccurrence()
    return await cross_document_bridges()
