"""Improved entity resolution with token_set_ratio, per-type thresholds,
domain aliases, and phonetic matching for voice-sourced content.
"""

from __future__ import annotations

import logging
from typing import Any

from rapidfuzz import fuzz

from .alias_dict import build_alias_dict, canonicalize

logger = logging.getLogger(__name__)

# Per-entity-type fuzzy thresholds
FUZZY_THRESHOLDS: dict[str, float] = {
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
    """Return the fuzzy match threshold for a given entity type."""
    return FUZZY_THRESHOLDS.get(entity_type, FUZZY_THRESHOLDS["default"])


def phonetic_match(a: str, b: str) -> bool:
    """Check if two strings match phonetically using Double Metaphone.

    Only useful for voice-sourced content where homophones are common.
    """
    try:
        from metaphone import doublemetaphone
        codes_a = doublemetaphone(a)
        codes_b = doublemetaphone(b)
        return bool(codes_a[0] and codes_b[0] and codes_a[0] == codes_b[0])
    except ImportError:
        logger.warning("metaphone not installed — phonetic matching disabled")
        return False


def resolve_entities(
    entities: list[dict[str, Any]],
    domain: str = "",
    source_type: str = "text",
) -> list[dict[str, Any]]:
    """Deduplicate entities using improved fuzzy matching.

    Steps:
      1. Canonicalize names via domain alias dict
      2. Group by entity type
      3. Within each type, fuzzy match using token_set_ratio
      4. For audio/voice source types, also check phonetic match
      5. Merge duplicates (keep first occurrence, combine properties)

    Returns deduplicated entity list.
    """
    if not entities:
        return []

    aliases = build_alias_dict(domain)

    # Canonicalize all names first
    for entity in entities:
        original = entity.get("name", "")
        entity["name"] = canonicalize(original, aliases)
        if entity["name"] != original:
            entity.setdefault("aliases", []).append(original)

    # Group by type
    by_type: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        etype = entity.get("type", "Unknown")
        by_type.setdefault(etype, []).append(entity)

    resolved: list[dict[str, Any]] = []

    for etype, group in by_type.items():
        threshold = get_threshold(etype)
        merged_indices: set[int] = set()

        for i, entity_a in enumerate(group):
            if i in merged_indices:
                continue

            name_a = entity_a["name"]

            for j in range(i + 1, len(group)):
                if j in merged_indices:
                    continue

                name_b = group[j]["name"]

                # Token set ratio: handles "Con Ed" vs "Con Edison"
                score = fuzz.token_set_ratio(name_a, name_b) / 100.0

                # For audio/voice, also check phonetic
                is_phonetic = False
                if source_type in ("audio", "voice") and score < threshold:
                    is_phonetic = phonetic_match(name_a, name_b)

                if score >= threshold or is_phonetic:
                    # Merge: keep the longer name as canonical
                    if len(name_b) > len(name_a):
                        entity_a["name"] = name_b
                        entity_a.setdefault("aliases", []).append(name_a)
                    else:
                        entity_a.setdefault("aliases", []).append(name_b)

                    # Combine descriptions
                    desc_a = entity_a.get("description", "")
                    desc_b = group[j].get("description", "")
                    if desc_b and desc_b not in desc_a:
                        entity_a["description"] = f"{desc_a} {desc_b}".strip()

                    merged_indices.add(j)
                    logger.info(
                        "Merged '%s' into '%s' (score=%.2f, type=%s)",
                        name_b, entity_a["name"], score, etype,
                    )

            resolved.append(entity_a)

    return resolved
