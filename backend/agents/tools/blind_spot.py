"""Blind spot detection tool — find orphan nodes and underrepresented entity types.

Runs proactively at every 25-node milestone and on-demand.
"""

from __future__ import annotations

import logging
from typing import Any

from agents import context as ctx

logger = logging.getLogger(__name__)

# Expected entity types per domain
DOMAIN_EXPECTED_TYPES: dict[str, list[str]] = {
    "academia": ["Paper", "Author", "Concept", "Methodology", "Finding",
                 "Institution", "Dataset", "Hypothesis"],
    "medicine": ["Patient", "Diagnosis", "Treatment", "Biomarker", "Drug",
                 "Symptom", "Outcome", "Trial", "Institution"],
    "science": ["Paper", "Author", "Concept", "Methodology", "Finding",
                "Dataset", "Institution", "Theory"],
    "law": ["Case", "Regulation", "Person", "Organization", "Concept",
            "Institution", "Precedent"],
    "business": ["Company", "Person", "Product", "Market", "Strategy",
                 "Concept", "Institution"],
    "computer science": ["Paper", "Author", "Concept", "Technology",
                         "Algorithm", "Dataset", "Model", "Framework"],
    "default": ["Concept", "Person", "Organization", "Paper", "Institution"],
}


def _get_expected_types(domain: str) -> list[str]:
    """Get expected entity types for a domain."""
    domain_lower = domain.lower()
    for key, types in DOMAIN_EXPECTED_TYPES.items():
        if key in domain_lower:
            return types
    return DOMAIN_EXPECTED_TYPES["default"]


async def detect_blind_spots(domain: str = "") -> dict[str, Any]:
    """Detect blind spots in the knowledge graph.

    Returns:
      - orphan_nodes: nodes with no connections
      - missing_types: expected entity types with few/no nodes
      - coverage_percent: estimated domain coverage
    """
    client = ctx.neo4j_client
    if client is None:
        return {"error": "Neo4j not connected"}

    # Orphan nodes
    orphans = await client.execute_query(
        """
        MATCH (n)
        WHERE NOT (n)--()
          AND n.name IS NOT NULL
        RETURN n.name AS name, labels(n)[0] AS type,
               n.collection_name AS collection,
               elementId(n) AS id
        ORDER BY n.ingested_at DESC
        LIMIT 20
        """
    )

    # Entity type coverage
    coverage = await client.execute_query(
        """
        MATCH (n)
        RETURN labels(n)[0] AS type, count(*) AS count
        ORDER BY count ASC
        """
    )

    # Total node count
    total_rows = await client.execute_query("MATCH (n) RETURN count(n) AS cnt")
    total_nodes = total_rows[0]["cnt"] if total_rows else 0

    # Analyze coverage vs expected types
    type_counts = {row["type"]: row["count"] for row in coverage if row.get("type")}
    expected_types = _get_expected_types(domain)

    missing_types = []
    for expected in expected_types:
        count = type_counts.get(expected, 0)
        if count < 3:
            missing_types.append({
                "type": expected,
                "count": count,
                "status": "absent" if count == 0 else "underrepresented",
            })

    present_count = sum(1 for t in expected_types if type_counts.get(t, 0) >= 3)
    coverage_pct = round((present_count / len(expected_types)) * 100) if expected_types else 0

    return {
        "orphan_nodes": orphans,
        "orphan_count": len(orphans),
        "missing_types": missing_types,
        "coverage_percent": coverage_pct,
        "total_nodes": total_nodes,
        "type_distribution": type_counts,
    }


async def check_blind_spot_milestone(domain: str = "") -> dict[str, Any] | None:
    """Check if we've hit a 25-node milestone and should report blind spots.

    Returns blind spot data if at a milestone, None otherwise.
    """
    client = ctx.neo4j_client
    if client is None:
        return None

    total_rows = await client.execute_query("MATCH (n) RETURN count(n) AS cnt")
    total = total_rows[0]["cnt"] if total_rows else 0

    if total > 0 and total % 25 == 0:
        return await detect_blind_spots(domain)
    return None
