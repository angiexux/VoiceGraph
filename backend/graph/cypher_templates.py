"""Pre-built Cypher query templates for VoiceGraph.

Each template uses Neo4j parameter syntax ($param) for safe injection.
Use ``get_template(name)`` to retrieve a template by key.
"""

from __future__ import annotations

CYPHER_TEMPLATES: dict[str, str] = {
    # ------------------------------------------------------------------
    # Read queries
    # ------------------------------------------------------------------
    "explore_entity": (
        "MATCH (n)-[r]-(m) "
        "WHERE n.name =~ '(?i).*' + $name + '.*' "
        "WITH n, r, m, 1 AS depth "
        "RETURN elementId(n) AS source_id, n.name AS source_name, labels(n) AS source_labels, "
        "type(r) AS rel_type, properties(r) AS rel_props, "
        "elementId(m) AS target_id, m.name AS target_name, labels(m) AS target_labels, "
        "properties(m) AS target_props "
        "LIMIT 50"
    ),
    "find_path": (
        "MATCH (a), (b) "
        "WHERE a.name =~ '(?i).*' + $from_name + '.*' "
        "AND b.name =~ '(?i).*' + $to_name + '.*' "
        "WITH a, b LIMIT 1 "
        "MATCH path = shortestPath((a)-[*1..$max_hops]-(b)) "
        "RETURN [n IN nodes(path) | {id: elementId(n), name: n.name, labels: labels(n)}] AS nodes, "
        "[r IN relationships(path) | {id: elementId(r), type: type(r), "
        "source: elementId(startNode(r)), target: elementId(endNode(r))}] AS edges"
    ),
    "entity_types": (
        "MATCH (n) "
        "RETURN DISTINCT labels(n) AS types, count(n) AS count "
        "ORDER BY count DESC"
    ),
    "most_connected": (
        "MATCH (n)-[r]-() "
        "RETURN elementId(n) AS id, n.name AS name, labels(n) AS labels, "
        "count(r) AS connections "
        "ORDER BY connections DESC "
        "LIMIT 20"
    ),
    "search_by_name": (
        "MATCH (n) "
        "WHERE n.name =~ '(?i).*' + $name + '.*' "
        "RETURN elementId(n) AS id, n.name AS name, labels(n) AS labels, "
        "properties(n) AS properties "
        "LIMIT 25"
    ),
    "full_graph": (
        "MATCH (n) "
        "OPTIONAL MATCH (n)-[r]->(m) "
        "RETURN elementId(n) AS n_id, labels(n) AS n_labels, properties(n) AS n_props, "
        "elementId(r) AS r_id, type(r) AS r_type, properties(r) AS r_props, "
        "elementId(m) AS m_id, labels(m) AS m_labels, properties(m) AS m_props "
        "LIMIT $limit"
    ),
    "node_details": (
        "MATCH (n) WHERE elementId(n) = $node_id "
        "OPTIONAL MATCH (n)-[r]-(m) "
        "RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS properties, "
        "collect(DISTINCT {rel_id: elementId(r), rel_type: type(r), rel_props: properties(r), "
        "neighbor_id: elementId(m), neighbor_name: m.name, neighbor_labels: labels(m)}) AS neighbors"
    ),
    # ------------------------------------------------------------------
    # Write queries
    # ------------------------------------------------------------------
    "merge_entity": (
        "CALL apoc.merge.node([$label], {name: $name}, $props, {}) "
        "YIELD node "
        "RETURN elementId(node) AS id, labels(node) AS labels, properties(node) AS properties"
    ),
    "merge_relationship": (
        "MATCH (a) WHERE elementId(a) = $from_id "
        "MATCH (b) WHERE elementId(b) = $to_id "
        "CALL apoc.merge.relationship(a, $rel_type, {}, $props, b, {}) "
        "YIELD rel "
        "RETURN elementId(rel) AS id, type(rel) AS type"
    ),
    "delete_entity_graph": (
        "MATCH (n) "
        "WHERE NOT any(l IN labels(n) WHERE l IN ['Document', 'Chunk']) "
        "DETACH DELETE n "
        "RETURN count(n) AS deleted_count"
    ),
}


def get_template(name: str) -> str:
    """Return a Cypher template by name.

    Raises:
        KeyError: If the template name is not found.
    """
    if name not in CYPHER_TEMPLATES:
        available = ", ".join(sorted(CYPHER_TEMPLATES.keys()))
        raise KeyError(
            f"Unknown Cypher template '{name}'. Available: {available}"
        )
    return CYPHER_TEMPLATES[name]
