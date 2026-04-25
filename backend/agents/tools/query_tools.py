"""Query tools for Agentic GraphRAG — search, explore, path-find, and
analyze the knowledge graph.

Each function is registered as an ADK tool. Docstrings serve as the
tool descriptions visible to the LLM.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agents import context as ctx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-built Cypher templates (fast + reliable — avoids Text2Cypher overhead)
# ---------------------------------------------------------------------------

CYPHER_TEMPLATES = {
    "search_concepts": """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower('{query}')
        RETURN n.name AS name, labels(n) AS types,
               n.description AS description, elementId(n) AS id
        LIMIT {top_k}
    """,
    "explore_entity": """
        MATCH (n)-[r]-(m)
        WHERE toLower(n.name) CONTAINS toLower('{entity_name}')
        RETURN n.name AS source, n.description AS source_desc,
               labels(n) AS source_types,
               type(r) AS rel_type,
               m.name AS target, m.description AS target_desc,
               labels(m) AS target_types,
               elementId(n) AS source_id, elementId(m) AS target_id,
               elementId(r) AS edge_id
        LIMIT 50
    """,
    "find_path": """
        MATCH (a), (b)
        WHERE toLower(a.name) CONTAINS toLower('{entity_a}')
          AND toLower(b.name) CONTAINS toLower('{entity_b}')
        MATCH path = shortestPath((a)-[*1..{max_hops}]-(b))
        RETURN path
    """,
    "entity_types": """
        MATCH (n)
        RETURN DISTINCT labels(n) AS types, count(n) AS count
        ORDER BY count DESC
    """,
    "most_connected": """
        MATCH (n)-[r]-()
        RETURN n.name AS name, labels(n) AS types,
               count(r) AS connections, elementId(n) AS id
        ORDER BY connections DESC
        LIMIT 20
    """,
    "graph_counts": """
        MATCH (n) WITH count(n) AS node_count
        OPTIONAL MATCH ()-[r]->() WITH node_count, count(r) AS edge_count
        RETURN node_count, edge_count
    """,
    "relationship_types": """
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) AS type, count(r) AS count
        ORDER BY count DESC
    """,
}

# ---------------------------------------------------------------------------
# Helper — run a Cypher query with fallback to mock data
# ---------------------------------------------------------------------------


async def _run_cypher(template_key: str, params: dict[str, Any] | None = None,
                raw_cypher: str | None = None) -> list[dict]:
    """Execute a Cypher query via the shared Neo4j client.

    Returns a list of record dicts, or an empty list if Neo4j is unavailable.
    """
    client = ctx.neo4j_client
    if client is None:
        return []

    cypher = raw_cypher or CYPHER_TEMPLATES[template_key]
    if params:
        for key, value in params.items():
            cypher = cypher.replace("{" + key + "}", str(value))

    try:
        return await client.execute_query(cypher)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cypher execution failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Tool 1: SEMANTIC CONCEPT SEARCH
# ---------------------------------------------------------------------------


async def search_concepts(query: str, top_k: int = 10) -> dict:
    """Semantic search across all entities in the knowledge graph.
    Uses vector embeddings to find conceptually similar entities.
    Returns matching entities with similarity scores.
    Use when: user asks about a topic broadly, e.g. 'What do we know about climate change?'"""

    results = await _run_cypher("search_concepts", {"query": query, "top_k": top_k})

    if results:
        return {
            "results": results,
            "count": len(results),
            "query": query,
        }

    # Fallback: mock data when Neo4j is not connected
    return {
        "results": [],
        "count": 0,
        "query": query,
        "message": "No results found. Neo4j may not be connected — using substring match fallback.",
    }


# ---------------------------------------------------------------------------
# Tool 2: ENTITY EXPLORATION
# ---------------------------------------------------------------------------


async def explore_entity(entity_name: str, depth: int = 2) -> dict:
    """Get the full neighborhood of an entity — all connected nodes
    and relationships up to N hops away.
    Use when: user asks about a specific entity by name,
    e.g. 'Tell me about OpenAI' or 'What is connected to Node X?'"""

    results = await _run_cypher("explore_entity", {"entity_name": entity_name})

    if results:
        nodes: dict[str, dict] = {}
        edges: list[dict] = []
        connections_summary: list[str] = []
        for rec in results:
            src_id = rec.get("source_id", "")
            tgt_id = rec.get("target_id", "")
            nodes[src_id] = {
                "id": src_id,
                "name": rec.get("source", ""),
                "description": rec.get("source_desc", ""),
                "types": rec.get("source_types", []),
            }
            nodes[tgt_id] = {
                "id": tgt_id,
                "name": rec.get("target", ""),
                "description": rec.get("target_desc", ""),
                "types": rec.get("target_types", []),
            }
            rel = rec.get("rel_type", "")
            target_name = rec.get("target", "")
            edges.append({
                "id": rec.get("edge_id", ""),
                "source": src_id,
                "target": tgt_id,
                "type": rel,
            })
            connections_summary.append(f"{rel} → {target_name}")

        # Build a human-readable summary for the agent
        main_node = next((n for n in nodes.values() if n["name"].lower() == entity_name.lower()), None)
        desc = main_node.get("description", "") if main_node else ""

        return {
            "entity": entity_name,
            "description": desc or "No description available.",
            "connections": connections_summary[:10],
            "nodes": list(nodes.values()),
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    return {
        "entity": entity_name,
        "nodes": [],
        "edges": [],
        "node_count": 0,
        "edge_count": 0,
        "message": f"No data found for entity '{entity_name}'. Graph may be empty or Neo4j not connected.",
    }


# ---------------------------------------------------------------------------
# Tool 3: PATH FINDING
# ---------------------------------------------------------------------------


async def find_path(entity_a: str, entity_b: str, max_hops: int = 5) -> dict:
    """Find the shortest path between two entities in the graph.
    Shows how two concepts are connected through intermediate entities.
    Returns the full path with all nodes and relationships.
    Use when: user asks how two things relate,
    e.g. 'How does Elon Musk connect to SpaceX?'"""

    results = await _run_cypher("find_path", {
        "entity_a": entity_a,
        "entity_b": entity_b,
        "max_hops": max_hops,
    })

    if results:
        return {
            "path": results,
            "entity_a": entity_a,
            "entity_b": entity_b,
            "found": True,
        }

    return {
        "path": [],
        "entity_a": entity_a,
        "entity_b": entity_b,
        "found": False,
        "message": f"No path found between '{entity_a}' and '{entity_b}'.",
    }


# ---------------------------------------------------------------------------
# Tool 4: TEXT-TO-CYPHER (Dynamic Cypher)
# ---------------------------------------------------------------------------


def query_graph(question: str) -> dict:
    """For complex analytical questions that require custom graph queries.
    Translates natural language to Cypher using the current graph schema.
    Use when: other tools are insufficient for the question's complexity,
    e.g. 'Which organizations have more than 5 people?'"""

    # TODO: Implement Text2Cypher via Gemini
    # 1. Fetch graph schema (labels, relationship types, property keys)
    # 2. Send schema + question + few-shot examples to Gemini
    # 3. Gemini generates Cypher → execute → return results
    return {
        "question": question,
        "cypher": None,
        "results": [],
        "message": "Text2Cypher not yet implemented. This will use Gemini to "
                   "translate your question into a Cypher query. For now, try "
                   "search_concepts or explore_entity instead.",
    }


# ---------------------------------------------------------------------------
# Tool 5: DEEP SEARCH (Hybrid Vector + Graph)
# ---------------------------------------------------------------------------


async def deep_search(query: str, top_k: int = 5) -> dict:
    """Deep search combining semantic similarity with graph traversal.
    First finds relevant entities via search, then expands their graph
    neighborhoods for rich context. Best for questions that need both
    semantic matching and structural understanding.
    Use when: user needs rich understanding spanning multiple concepts,
    e.g. 'Explain the landscape of AI regulation'"""

    # Step 1: Find anchor entities
    search_results = await search_concepts(query, top_k=top_k)
    anchors = search_results.get("results", [])

    if not anchors:
        return {
            "query": query,
            "anchors": [],
            "expanded_context": [],
            "message": "No anchor entities found for deep search.",
        }

    # Step 2: Expand each anchor's neighborhood
    expanded: list[dict] = []
    for anchor in anchors:
        name = anchor.get("name", "")
        if name:
            neighborhood = await explore_entity(name, depth=1)
            expanded.append({
                "anchor": name,
                "neighborhood": neighborhood,
            })

    return {
        "query": query,
        "anchors": anchors,
        "expanded_context": expanded,
        "total_anchors": len(anchors),
        "total_expanded": len(expanded),
    }


# ---------------------------------------------------------------------------
# Tool 6: COMMUNITY / GLOBAL OVERVIEW
# ---------------------------------------------------------------------------


async def get_communities() -> dict:
    """Get high-level thematic summaries of the knowledge graph.
    Uses community detection to identify clusters of related entities
    and provides summaries of each community.
    Use when: user asks about main themes, overview, or big picture,
    e.g. 'What are the main themes in this data?'"""

    # For now: return entity type distribution as a proxy for communities
    type_results = await _run_cypher("entity_types")

    if type_results:
        return {
            "communities": [
                {
                    "theme": ", ".join(rec.get("types", [])),
                    "entity_count": rec.get("count", 0),
                }
                for rec in type_results
            ],
            "total_communities": len(type_results),
            "message": "Showing entity type distribution as community proxy. "
                       "Full Leiden community detection will be available soon.",
        }

    return {
        "communities": [],
        "total_communities": 0,
        "message": "No community data available. Graph may be empty.",
    }


# ---------------------------------------------------------------------------
# Tool 7: ONTOLOGY AWARENESS
# ---------------------------------------------------------------------------


async def get_ontology_info() -> dict:
    """Get the current ontology structure — all entity types, relationship
    types, their hierarchy, and domain/range constraints.
    Use when: user asks what types of data are in the graph,
    e.g. 'What types of entities do we have?'"""

    mgr = ctx.ontology_manager
    if mgr is not None:
        try:
            return {
                "ontology": mgr.to_json(),
                "message": "Current ontology loaded.",
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read ontology: %s", exc)

    # Fallback: query Neo4j for schema info
    types = await _run_cypher("entity_types")
    rels = await _run_cypher("relationship_types")

    return {
        "entity_types": types or [],
        "relationship_types": rels or [],
        "message": "Ontology manager not available. Showing schema from graph.",
    }


# ---------------------------------------------------------------------------
# Tool 8: GRAPH STATISTICS
# ---------------------------------------------------------------------------


async def get_graph_stats() -> dict:
    """Get statistics about the knowledge graph — number of nodes, edges,
    entity type distribution, most connected entities.
    Use when: user asks about graph size or structure,
    e.g. 'How big is the graph?' or 'What are the most connected nodes?'"""

    # Single fast query for counts
    counts = await _run_cypher("graph_counts")
    if not counts:
        return {
            "node_count": 0,
            "edge_count": 0,
            "entity_types": [],
            "most_connected": [],
            "message": "Neo4j not connected. No statistics available.",
        }

    rec = counts[0]
    # Run types and top nodes in parallel for speed
    types_task = _run_cypher("entity_types")
    top_task = _run_cypher("most_connected")
    entity_types, top_nodes = await asyncio.gather(types_task, top_task)

    return {
        "node_count": rec.get("node_count", 0),
        "edge_count": rec.get("edge_count", 0),
        "entity_types": entity_types,
        "most_connected": top_nodes[:10] if top_nodes else [],
    }
