"""GraphRAG retrieval: vector similarity → anchor nodes → subgraph expansion."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def graphrag_search(
    query: str,
    neo4j_client: Any,
    top_k: int = 5,
    hop_depth: int = 2,
) -> dict[str, Any]:
    """
    1. Embed query → find anchor nodes via Neo4j vector index.
    2. Expand hop_depth hops from each anchor.
    3. Return anchors + subgraph context string ready for LLM prompting.
    """
    _empty: dict[str, Any] = {
        "anchors": [], "subgraph_context": "", "nodes": [], "edges": [],
    }

    if neo4j_client is None or not neo4j_client.available:
        return _empty

    # Step 1: vector search for anchor nodes
    from retrieval.embedder import get_embedding

    query_embedding = await get_embedding(query)
    anchor_nodes: list[dict[str, Any]] = []

    if query_embedding:
        try:
            anchor_nodes = await neo4j_client.execute_query(
                """
                CALL db.index.vector.queryNodes('entity_embeddings', $top_k, $embedding)
                YIELD node, score
                RETURN elementId(node) AS id, node.name AS name,
                       node.description AS description,
                       labels(node) AS types, score
                ORDER BY score DESC
                """,
                {"top_k": top_k, "embedding": query_embedding},
            )
        except Exception as exc:
            logger.debug("Vector index query failed (index may not exist yet): %s", exc)

    # Fallback: substring match when vector index unavailable
    if not anchor_nodes:
        anchor_nodes = await neo4j_client.execute_query(
            """
            MATCH (n)
            WHERE toLower(n.name) CONTAINS toLower($query)
            RETURN elementId(n) AS id, node.name AS name,
                   n.description AS description,
                   labels(n) AS types, 1.0 AS score
            LIMIT $top_k
            """,
            {"query": query, "top_k": top_k},
        )

    if not anchor_nodes:
        return _empty

    # Step 2: multi-hop expansion around anchors
    anchor_ids = [n["id"] for n in anchor_nodes if n.get("id")]
    expansion: list[dict[str, Any]] = []

    # Simple 1-hop expansion (compatible with all Neo4j 5.x versions)
    try:
        expansion = await neo4j_client.execute_query(
            f"""
            MATCH (anchor)-[rel*1..{hop_depth}]-(connected)
            WHERE elementId(anchor) IN $anchor_ids
            RETURN DISTINCT
                anchor.name AS anchor_name,
                elementId(connected) AS node_id,
                connected.name AS node_name,
                connected.description AS node_desc,
                labels(connected) AS node_types,
                type(rel[0]) AS rel_type,
                elementId(startNode(rel[0])) AS rel_source,
                elementId(endNode(rel[0])) AS rel_target
            LIMIT 150
            """,
            {"anchor_ids": anchor_ids},
        )
    except Exception as exc:
        logger.warning("GraphRAG expansion failed, using 1-hop fallback: %s", exc)
        for anchor in anchor_nodes[:3]:
            name = anchor.get("name", "")
            if not name:
                continue
            try:
                rows = await neo4j_client.execute_query(
                    """
                    MATCH (n)-[r]-(m)
                    WHERE toLower(n.name) CONTAINS toLower($name)
                    RETURN n.name AS anchor_name, elementId(m) AS node_id,
                           m.name AS node_name, m.description AS node_desc,
                           labels(m) AS node_types, type(r) AS rel_type,
                           elementId(startNode(r)) AS rel_source,
                           elementId(endNode(r)) AS rel_target
                    LIMIT 30
                    """,
                    {"name": name},
                )
                expansion.extend(rows)
            except Exception:
                pass

    # Step 3: build context string + deduplicated node/edge lists
    nodes_seen: dict[str, dict[str, Any]] = {}
    edges_seen: list[dict[str, Any]] = []
    triples: list[str] = []

    for row in expansion:
        nid = row.get("node_id", "")
        nname = row.get("node_name", "") or ""
        ndesc = row.get("node_desc", "") or ""
        anchor_name = row.get("anchor_name", "")
        rel_type = row.get("rel_type", "RELATED_TO")

        if nid and nid not in nodes_seen:
            nodes_seen[nid] = {
                "id": nid, "name": nname,
                "description": ndesc,
                "types": row.get("node_types", []),
            }
        if row.get("rel_source") and row.get("rel_target"):
            edges_seen.append({
                "source": row["rel_source"],
                "target": row["rel_target"],
                "type": rel_type,
            })
        if anchor_name and nname:
            triples.append(
                f"({anchor_name})-[{rel_type}]->({nname}): {ndesc[:100]}"
            )

    return {
        "anchors": anchor_nodes,
        "subgraph_context": "\n".join(triples[:60]),
        "nodes": list(nodes_seen.values()),
        "edges": edges_seen,
    }
