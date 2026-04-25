"""Async Neo4j client for the VoiceGraph knowledge graph.

Provides a high-level async interface on top of the official Neo4j Python
driver.  When Neo4j is unreachable the client falls back to deterministic
sample data so the frontend can render something useful during development.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sample / fallback data
# ---------------------------------------------------------------------------

_SAMPLE_NODES: list[dict[str, Any]] = [
    {"id": "s-1", "labels": ["Concept"], "properties": {"name": "Artificial Intelligence", "description": "The simulation of human intelligence by machines"}},
    {"id": "s-2", "labels": ["Concept"], "properties": {"name": "Machine Learning", "description": "Subset of AI focused on learning from data"}},
    {"id": "s-3", "labels": ["Concept"], "properties": {"name": "Deep Learning", "description": "ML using multi-layer neural networks"}},
    {"id": "s-4", "labels": ["Concept"], "properties": {"name": "Natural Language Processing", "description": "AI for understanding human language"}},
    {"id": "s-5", "labels": ["Concept"], "properties": {"name": "Computer Vision", "description": "AI for interpreting visual information"}},
    {"id": "s-6", "labels": ["Technology"], "properties": {"name": "Neural Networks", "description": "Computing systems inspired by biological neural networks"}},
    {"id": "s-7", "labels": ["Technology"], "properties": {"name": "Transformers", "description": "Attention-based neural network architecture"}},
    {"id": "s-8", "labels": ["Technology"], "properties": {"name": "Convolutional Neural Networks", "description": "Neural networks for grid-like data"}},
    {"id": "s-9", "labels": ["Application"], "properties": {"name": "ChatGPT", "description": "Large language model chatbot by OpenAI"}},
    {"id": "s-10", "labels": ["Application"], "properties": {"name": "DALL-E", "description": "AI image generation model"}},
    {"id": "s-11", "labels": ["Organization"], "properties": {"name": "OpenAI", "description": "AI research organization"}},
    {"id": "s-12", "labels": ["Organization"], "properties": {"name": "Google DeepMind", "description": "AI research laboratory"}},
    {"id": "s-13", "labels": ["Person"], "properties": {"name": "Geoffrey Hinton", "description": "Pioneer of deep learning"}},
    {"id": "s-14", "labels": ["Person"], "properties": {"name": "Yann LeCun", "description": "Pioneer of convolutional neural networks"}},
    {"id": "s-15", "labels": ["Concept"], "properties": {"name": "Reinforcement Learning", "description": "ML paradigm based on reward signals"}},
]

_SAMPLE_EDGES: list[dict[str, Any]] = [
    {"id": "e-1", "type": "SUBFIELD_OF", "source": "s-2", "target": "s-1", "properties": {}},
    {"id": "e-2", "type": "SUBFIELD_OF", "source": "s-3", "target": "s-2", "properties": {}},
    {"id": "e-3", "type": "SUBFIELD_OF", "source": "s-4", "target": "s-1", "properties": {}},
    {"id": "e-4", "type": "SUBFIELD_OF", "source": "s-5", "target": "s-1", "properties": {}},
    {"id": "e-5", "type": "USES", "source": "s-3", "target": "s-6", "properties": {}},
    {"id": "e-6", "type": "TYPE_OF", "source": "s-7", "target": "s-6", "properties": {}},
    {"id": "e-7", "type": "TYPE_OF", "source": "s-8", "target": "s-6", "properties": {}},
    {"id": "e-8", "type": "USES", "source": "s-4", "target": "s-7", "properties": {}},
    {"id": "e-9", "type": "USES", "source": "s-5", "target": "s-8", "properties": {}},
    {"id": "e-10", "type": "BUILT_BY", "source": "s-9", "target": "s-11", "properties": {}},
    {"id": "e-11", "type": "BUILT_BY", "source": "s-10", "target": "s-11", "properties": {}},
    {"id": "e-12", "type": "INSTANCE_OF", "source": "s-9", "target": "s-4", "properties": {}},
    {"id": "e-13", "type": "INSTANCE_OF", "source": "s-10", "target": "s-5", "properties": {}},
    {"id": "e-14", "type": "PIONEERED", "source": "s-13", "target": "s-3", "properties": {}},
    {"id": "e-15", "type": "PIONEERED", "source": "s-14", "target": "s-8", "properties": {}},
    {"id": "e-16", "type": "WORKS_AT", "source": "s-13", "target": "s-12", "properties": {}},
    {"id": "e-17", "type": "SUBFIELD_OF", "source": "s-15", "target": "s-2", "properties": {}},
]

# ---------------------------------------------------------------------------
# Helpers for transforming Neo4j records
# ---------------------------------------------------------------------------


def _node_dict(node: Any) -> dict[str, Any]:
    """Convert a neo4j.graph.Node to a plain dict."""
    return {
        "id": node.element_id,
        "labels": list(node.labels),
        "properties": dict(node),
    }


def _rel_dict(rel: Any) -> dict[str, Any]:
    """Convert a neo4j.graph.Relationship to a plain dict."""
    return {
        "id": rel.element_id,
        "type": rel.type,
        "source": rel.start_node.element_id,
        "target": rel.end_node.element_id,
        "properties": dict(rel),
    }


# ---------------------------------------------------------------------------
# Neo4jClient
# ---------------------------------------------------------------------------


class Neo4jClient:
    """Thin async wrapper around the Neo4j Python driver.

    Reads connection details from environment variables:
      - NEO4J_URI   (default: bolt://localhost:7687)
      - NEO4J_USERNAME (default: neo4j)
      - NEO4J_PASSWORD (default: "")

    When the driver cannot connect the client transparently returns sample
    data so the rest of the application keeps working.
    """

    def __init__(self) -> None:
        self._uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._username = os.getenv("NEO4J_USERNAME", "neo4j")
        self._password = os.getenv("NEO4J_PASSWORD", "")
        self._driver: Any = None
        self._available: bool = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """True when a live Neo4j connection is established."""
        return self._available

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open a connection pool to Neo4j.

        Silently falls back to sample data if Neo4j is unreachable.
        """
        try:
            from neo4j import AsyncGraphDatabase  # type: ignore[import-untyped]

            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._username, self._password),
                max_connection_pool_size=50,
                connection_acquisition_timeout=5,
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            self._available = True
            logger.info("Neo4j connected at %s", self._uri)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Neo4j unavailable (%s) — using sample data fallback.", exc
            )
            self._driver = None
            self._available = False

    async def close(self) -> None:
        """Shut down the driver and release all connections."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            self._available = False
            logger.info("Neo4j driver closed.")

    # ------------------------------------------------------------------
    # Core query execution
    # ------------------------------------------------------------------

    async def execute_query(
        self,
        cypher: str,
        params: dict[str, Any] | None = None,
        database: str = "neo4j",
    ) -> list[dict[str, Any]]:
        """Run a Cypher query and return results as a list of dicts.

        Returns an empty list when the driver is not available.
        """
        if not self._available or self._driver is None:
            logger.warning("Neo4j driver unavailable — returning empty result.")
            return []

        async with self._driver.session(database=database) as session:
            result = await session.run(cypher, params or {})
            records = await result.data()
            return records

    # ------------------------------------------------------------------
    # High-level graph operations
    # ------------------------------------------------------------------

    async def get_full_graph(self, limit: int = 5000) -> dict[str, Any]:
        """Return all nodes and edges for the frontend visualisation.

        Falls back to sample data when Neo4j is unavailable.
        """
        if not self._available:
            return {"nodes": _SAMPLE_NODES, "edges": _SAMPLE_EDGES}

        cypher = (
            "MATCH (n) "
            "OPTIONAL MATCH (n)-[r]->(m) "
            "RETURN n, r, m "
            "LIMIT $limit"
        )
        async with self._driver.session(database="neo4j") as session:
            result = await session.run(cypher, {"limit": limit})
            records = [record async for record in result]

        nodes_map: dict[str, dict] = {}
        edges_list: list[dict] = []

        for record in records:
            n = record.get("n")
            r = record.get("r")
            m = record.get("m")

            if n is not None and n.element_id not in nodes_map:
                nodes_map[n.element_id] = _node_dict(n)
            if m is not None and m.element_id not in nodes_map:
                nodes_map[m.element_id] = _node_dict(m)
            if r is not None:
                edges_list.append(_rel_dict(r))

        return {"nodes": list(nodes_map.values()), "edges": edges_list}

    async def get_node_details(self, node_id: str) -> dict[str, Any]:
        """Return a single node with all its properties and neighbours.

        Falls back to sample data lookup.
        """
        if not self._available:
            for node in _SAMPLE_NODES:
                if node["id"] == node_id:
                    neighbors = [
                        e for e in _SAMPLE_EDGES
                        if e["source"] == node_id or e["target"] == node_id
                    ]
                    return {**node, "neighbors": neighbors}
            return {}

        cypher = (
            "MATCH (n) WHERE elementId(n) = $node_id "
            "OPTIONAL MATCH (n)-[r]-(m) "
            "RETURN n, collect({rel: r, neighbor: m}) AS connections"
        )
        async with self._driver.session(database="neo4j") as session:
            result = await session.run(cypher, {"node_id": node_id})
            record = await result.single()

        if record is None:
            return {}

        n = record["n"]
        connections = record["connections"]
        neighbors = []
        for conn in connections:
            rel = conn.get("rel")
            neighbor = conn.get("neighbor")
            if rel is not None and neighbor is not None:
                neighbors.append({
                    "rel_id": rel.element_id,
                    "rel_type": rel.type,
                    "rel_props": dict(rel),
                    "neighbor_id": neighbor.element_id,
                    "neighbor_name": neighbor.get("name", ""),
                    "neighbor_labels": list(neighbor.labels),
                })

        return {
            "id": n.element_id,
            "labels": list(n.labels),
            "properties": dict(n),
            "neighbors": neighbors,
        }

    async def find_entity(self, name: str) -> list[dict[str, Any]]:
        """Fuzzy-match entities by name (case-insensitive).

        Falls back to substring search in sample data.
        """
        if not self._available:
            lower = name.lower()
            return [
                n for n in _SAMPLE_NODES
                if lower in n["properties"].get("name", "").lower()
            ]

        cypher = (
            "MATCH (n) "
            "WHERE toLower(n.name) CONTAINS toLower($name) "
            "RETURN elementId(n) AS id, n.name AS name, labels(n) AS labels, "
            "properties(n) AS properties "
            "LIMIT 25"
        )
        return await self.execute_query(cypher, {"name": name})

    async def shortest_path(
        self, from_name: str, to_name: str, max_hops: int = 6
    ) -> dict[str, Any]:
        """Find the shortest path between two entities by name.

        Falls back to a simple BFS on sample data edges.
        """
        if not self._available:
            return self._sample_shortest_path(from_name, to_name)

        cypher = (
            "MATCH (a), (b) "
            "WHERE toLower(a.name) CONTAINS toLower($from_name) "
            "AND toLower(b.name) CONTAINS toLower($to_name) "
            "WITH a, b LIMIT 1 "
            f"MATCH path = shortestPath((a)-[*1..{max_hops}]-(b)) "
            "RETURN [n IN nodes(path) | "
            "  {id: elementId(n), name: n.name, labels: labels(n)}] AS nodes, "
            "[r IN relationships(path) | "
            "  {id: elementId(r), type: type(r), "
            "   source: elementId(startNode(r)), target: elementId(endNode(r))}] AS edges"
        )
        rows = await self.execute_query(cypher, {
            "from_name": from_name,
            "to_name": to_name,
        })
        if rows:
            return {"nodes": rows[0]["nodes"], "edges": rows[0]["edges"]}
        return {"nodes": [], "edges": []}

    async def explore_neighborhood(
        self, name: str, depth: int = 2
    ) -> dict[str, Any]:
        """BFS expansion around a named entity up to *depth* hops.

        Falls back to sample data neighbourhood traversal.
        """
        if not self._available:
            return self._sample_neighborhood(name, depth)

        cypher = (
            "MATCH (start) WHERE toLower(start.name) CONTAINS toLower($name) "
            "WITH start LIMIT 1 "
            f"MATCH path = (start)-[*1..{depth}]-(connected) "
            "WITH start, connected, relationships(path) AS rels "
            "UNWIND rels AS r "
            "WITH start, collect(DISTINCT connected) AS neighbors, "
            "     collect(DISTINCT r) AS all_rels "
            "RETURN {id: elementId(start), name: start.name, labels: labels(start)} AS center, "
            "[n IN neighbors | {id: elementId(n), name: n.name, labels: labels(n)}] AS neighbors, "
            "[r IN all_rels | {id: elementId(r), type: type(r), "
            " source: elementId(startNode(r)), target: elementId(endNode(r))}] AS edges"
        )
        rows = await self.execute_query(cypher, {"name": name})
        if rows:
            return rows[0]
        return {"center": None, "neighbors": [], "edges": []}

    async def get_stats(self) -> dict[str, Any]:
        """Return summary statistics about the knowledge graph.

        Falls back to stats computed from sample data.
        """
        if not self._available:
            label_counts: dict[str, int] = {}
            for n in _SAMPLE_NODES:
                for lbl in n["labels"]:
                    label_counts[lbl] = label_counts.get(lbl, 0) + 1
            rel_counts: dict[str, int] = {}
            for e in _SAMPLE_EDGES:
                rel_counts[e["type"]] = rel_counts.get(e["type"], 0) + 1
            return {
                "node_count": len(_SAMPLE_NODES),
                "edge_count": len(_SAMPLE_EDGES),
                "label_distribution": label_counts,
                "relationship_distribution": rel_counts,
                "neo4j_connected": False,
            }

        node_count_rows = await self.execute_query("MATCH (n) RETURN count(n) AS cnt")
        edge_count_rows = await self.execute_query("MATCH ()-[r]->() RETURN count(r) AS cnt")
        label_rows = await self.execute_query(
            "MATCH (n) RETURN DISTINCT labels(n) AS types, count(n) AS count ORDER BY count DESC"
        )
        rel_rows = await self.execute_query(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC"
        )

        label_dist = {}
        for row in label_rows:
            key = ", ".join(row["types"]) if row["types"] else "Unlabeled"
            label_dist[key] = row["count"]

        rel_dist = {row["type"]: row["count"] for row in rel_rows}

        return {
            "node_count": node_count_rows[0]["cnt"] if node_count_rows else 0,
            "edge_count": edge_count_rows[0]["cnt"] if edge_count_rows else 0,
            "label_distribution": label_dist,
            "relationship_distribution": rel_dist,
            "neo4j_connected": True,
        }

    async def merge_node(
        self, label: str, properties: dict[str, Any]
    ) -> str:
        """MERGE a node by name + label and return its element ID.

        Uses simple MERGE without APOC for broader compatibility.
        """
        name = properties.get("name", "Unnamed")
        extra_props = {k: v for k, v in properties.items() if k != "name"}

        if not self._available:
            new_id = f"s-{len(_SAMPLE_NODES) + 1}"
            _SAMPLE_NODES.append({
                "id": new_id,
                "labels": [label],
                "properties": {"name": name, **extra_props},
            })
            return new_id

        set_clause = ""
        if extra_props:
            set_clause = "SET " + ", ".join(
                f"n.{k} = ${k}" for k in extra_props
            )

        cypher = (
            f"MERGE (n:`{label}` {{name: $name}}) "
            f"{set_clause} "
            "RETURN elementId(n) AS id"
        )
        params = {"name": name, **extra_props}
        rows = await self.execute_query(cypher, params)
        return rows[0]["id"] if rows else ""

    async def merge_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> str:
        """MERGE a relationship between two nodes (by element ID).

        Returns the element ID of the relationship.
        """
        properties = properties or {}

        if not self._available:
            new_id = f"e-{len(_SAMPLE_EDGES) + 1}"
            _SAMPLE_EDGES.append({
                "id": new_id,
                "type": rel_type,
                "source": from_id,
                "target": to_id,
                "properties": properties,
            })
            return new_id

        set_clause = ""
        if properties:
            set_clause = "SET " + ", ".join(
                f"r.{k} = ${k}" for k in properties
            )

        cypher = (
            "MATCH (a) WHERE elementId(a) = $from_id "
            "MATCH (b) WHERE elementId(b) = $to_id "
            f"MERGE (a)-[r:`{rel_type}`]->(b) "
            f"{set_clause} "
            "RETURN elementId(r) AS id"
        )
        params = {"from_id": from_id, "to_id": to_id, **properties}
        rows = await self.execute_query(cypher, params)
        return rows[0]["id"] if rows else ""

    # ------------------------------------------------------------------
    # Sample-data fallback helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sample_shortest_path(
        from_name: str, to_name: str
    ) -> dict[str, Any]:
        """BFS shortest path over sample data."""
        from_lower, to_lower = from_name.lower(), to_name.lower()
        start_id = next(
            (n["id"] for n in _SAMPLE_NODES
             if from_lower in n["properties"].get("name", "").lower()),
            None,
        )
        end_id = next(
            (n["id"] for n in _SAMPLE_NODES
             if to_lower in n["properties"].get("name", "").lower()),
            None,
        )
        if start_id is None or end_id is None:
            return {"nodes": [], "edges": []}

        # Build adjacency
        adj: dict[str, list[tuple[str, dict]]] = {}
        for e in _SAMPLE_EDGES:
            adj.setdefault(e["source"], []).append((e["target"], e))
            adj.setdefault(e["target"], []).append((e["source"], e))

        # BFS
        from collections import deque
        queue: deque[list[str]] = deque([[start_id]])
        visited = {start_id}
        while queue:
            path = queue.popleft()
            current = path[-1]
            if current == end_id:
                # Reconstruct
                node_map = {n["id"]: n for n in _SAMPLE_NODES}
                path_nodes = [node_map[nid] for nid in path if nid in node_map]
                path_edges = []
                for i in range(len(path) - 1):
                    for e in _SAMPLE_EDGES:
                        if (
                            (e["source"] == path[i] and e["target"] == path[i + 1])
                            or (e["source"] == path[i + 1] and e["target"] == path[i])
                        ):
                            path_edges.append(e)
                            break
                return {"nodes": path_nodes, "edges": path_edges}
            for neighbor_id, _ in adj.get(current, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(path + [neighbor_id])

        return {"nodes": [], "edges": []}

    @staticmethod
    def _sample_neighborhood(name: str, depth: int) -> dict[str, Any]:
        """Multi-hop neighborhood over sample data."""
        lower = name.lower()
        center = next(
            (n for n in _SAMPLE_NODES
             if lower in n["properties"].get("name", "").lower()),
            None,
        )
        if center is None:
            return {"center": None, "neighbors": [], "edges": []}

        visited = {center["id"]}
        frontier = {center["id"]}
        found_edges: list[dict] = []

        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                for e in _SAMPLE_EDGES:
                    other = None
                    if e["source"] == nid:
                        other = e["target"]
                    elif e["target"] == nid:
                        other = e["source"]
                    if other is not None:
                        found_edges.append(e)
                        if other not in visited:
                            visited.add(other)
                            next_frontier.add(other)
            frontier = next_frontier

        node_map = {n["id"]: n for n in _SAMPLE_NODES}
        neighbors = [
            node_map[nid] for nid in visited
            if nid != center["id"] and nid in node_map
        ]
        # Deduplicate edges
        seen_edge_ids: set[str] = set()
        unique_edges = []
        for e in found_edges:
            if e["id"] not in seen_edge_ids:
                seen_edge_ids.add(e["id"])
                unique_edges.append(e)

        return {
            "center": center,
            "neighbors": neighbors,
            "edges": unique_edges,
        }
