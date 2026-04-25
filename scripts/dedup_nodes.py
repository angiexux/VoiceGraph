#!/usr/bin/env python3
"""One-time duplicate node cleanup script.

Uses token_set_ratio fuzzy matching with per-entity-type thresholds
to find and merge duplicate nodes in Neo4j.

Usage:
    python scripts/dedup_nodes.py [--auto]

    --auto: Skip interactive confirmation, merge all detected duplicates.

Run this after any bulk population script to clean up cross-script duplicates.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from rapidfuzz import fuzz

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Per-entity-type thresholds (same as extraction/entity_resolution.py)
FUZZY_THRESHOLDS = {
    "Organization": 0.75,
    "Company": 0.75,
    "Person": 0.88,
    "Regulation": 0.95,
    "Concept": 0.72,
    "Paper": 0.90,
    "Author": 0.85,
    "default": 0.80,
}


def get_threshold(entity_type: str) -> float:
    return FUZZY_THRESHOLDS.get(entity_type, FUZZY_THRESHOLDS["default"])


async def main(auto: bool = False) -> None:
    from graph.neo4j_client import Neo4jClient

    client = Neo4jClient()
    await client.connect()

    if not client.available:
        logger.error("Could not connect to Neo4j. Check your .env file.")
        return

    logger.info("Connected to Neo4j. Scanning for duplicates...")

    # Get all nodes grouped by label
    rows = await client.execute_query(
        """
        MATCH (n)
        WHERE n.name IS NOT NULL
        RETURN elementId(n) AS id, n.name AS name, labels(n)[0] AS type
        ORDER BY type, name
        """
    )

    if not rows:
        logger.info("No nodes found.")
        return

    logger.info("Found %d nodes. Checking for duplicates...", len(rows))

    # Group by type
    by_type: dict[str, list[dict]] = {}
    for row in rows:
        t = row.get("type", "Unknown")
        by_type.setdefault(t, []).append(row)

    pairs_to_merge: list[tuple[dict, dict, float]] = []

    for etype, group in by_type.items():
        threshold = get_threshold(etype)
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                name_a = group[i]["name"]
                name_b = group[j]["name"]
                score = fuzz.token_set_ratio(name_a, name_b) / 100.0
                if score >= threshold and name_a.lower() != name_b.lower():
                    pairs_to_merge.append((group[i], group[j], score))

    if not pairs_to_merge:
        logger.info("No duplicates found!")
        return

    logger.info("Found %d potential duplicate pairs:", len(pairs_to_merge))

    merged_count = 0

    for node_a, node_b, score in pairs_to_merge:
        # Keep the one with the longer name
        if len(node_b["name"]) > len(node_a["name"]):
            keep, remove = node_b, node_a
        else:
            keep, remove = node_a, node_b

        print(f"\n  [{node_a['type']}] \"{node_a['name']}\" vs \"{node_b['name']}\" (score: {score:.2f})")
        print(f"    → Keep: \"{keep['name']}\" | Remove: \"{remove['name']}\"")

        if not auto:
            answer = input("    Merge? [y/N] ").strip().lower()
            if answer != "y":
                print("    Skipped.")
                continue

        # Try APOC merge first, fall back to manual
        try:
            await client.execute_query(
                """
                CALL apoc.refactor.mergeNodes(
                    [n IN [elementId($keep_id), elementId($remove_id)] | n],
                    {properties: "combine", mergeRels: true}
                )
                """,
                {"keep_id": keep["id"], "remove_id": remove["id"]},
            )
            merged_count += 1
            print("    Merged (APOC).")
        except Exception:
            # Manual merge: move relationships, delete duplicate
            try:
                # Move incoming relationships
                await client.execute_query(
                    """
                    MATCH (remove)-[r]->(other)
                    WHERE elementId(remove) = $remove_id
                    WITH remove, r, other, type(r) AS rtype, properties(r) AS props
                    MATCH (keep) WHERE elementId(keep) = $keep_id
                    CALL {
                        WITH keep, other, rtype
                        CREATE (keep)-[nr:RELATED_TO]->(other)
                        RETURN nr
                    }
                    DELETE r
                    """,
                    {"keep_id": keep["id"], "remove_id": remove["id"]},
                )
                await client.execute_query(
                    """
                    MATCH (other)-[r]->(remove)
                    WHERE elementId(remove) = $remove_id
                    WITH remove, r, other, type(r) AS rtype
                    MATCH (keep) WHERE elementId(keep) = $keep_id
                    CALL {
                        WITH other, keep, rtype
                        CREATE (other)-[nr:RELATED_TO]->(keep)
                        RETURN nr
                    }
                    DELETE r
                    """,
                    {"keep_id": keep["id"], "remove_id": remove["id"]},
                )
                # Delete the duplicate
                await client.execute_query(
                    "MATCH (n) WHERE elementId(n) = $id DETACH DELETE n",
                    {"id": remove["id"]},
                )
                merged_count += 1
                print("    Merged (manual).")
            except Exception as exc:
                logger.warning("    Failed to merge: %s", exc)

    logger.info("\nDone. Merged %d duplicate pairs.", merged_count)
    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deduplicate nodes in Neo4j")
    parser.add_argument("--auto", action="store_true", help="Skip interactive confirmation")
    args = parser.parse_args()
    asyncio.run(main(auto=args.auto))
