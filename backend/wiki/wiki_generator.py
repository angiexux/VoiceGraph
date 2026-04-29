"""Auto-generate structured wiki pages from ingested entities using Gemini."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


async def generate_wiki_page(
    job_id: str,
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    source_hint: str,
    neo4j_client: Any,
) -> dict[str, Any] | None:
    """Generate a wiki page from a completed ingestion job and store it in Neo4j.

    Args:
        job_id: The ingestion job ID (used as dedup key).
        entities: List of extracted entities {name, type, description}.
        relationships: List of extracted relationships {source, target, type, description}.
        source_hint: Source document name/URL for the page title.
        neo4j_client: Live Neo4j client for storing the WikiPage node.

    Returns:
        The generated wiki page dict, or None on failure.
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    if not entities:
        return None

    # Build concise summaries for the prompt
    entity_lines = "\n".join(
        f"- {e.get('name', '')} ({e.get('type', 'Entity')}): {e.get('description', '')[:120]}"
        for e in entities[:30]
    )
    rel_lines = "\n".join(
        f"- {r.get('source', '')} --[{r.get('type', '')}]--> {r.get('target', '')}: {r.get('description', '')[:80]}"
        for r in relationships[:20]
    )

    prompt = f"""You are creating a structured knowledge wiki page for a non-profit knowledge management system.

Based on these extracted entities and relationships from a document, generate a comprehensive wiki page in Markdown.

SOURCE: {source_hint}

ENTITIES:
{entity_lines}

RELATIONSHIPS:
{rel_lines}

Generate a wiki page with EXACTLY this structure (use these exact markdown headings):

# [Descriptive title based on content]

## Summary
2-3 paragraph executive summary of what this document covers and why it matters.

## Key Entities
| Name | Type | Description |
|------|------|-------------|
[table rows for top 10 entities]

## Key Relationships
Bullet list of the most significant connections found, explained in plain language for non-profit staff.

## Questions to Explore
1. [Specific question about this content]
2. [Another specific question]
3. [Another specific question]

## Related Topics
Comma-separated list of topics/themes this content connects to.

Output only the markdown, no preamble."""

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(response_mime_type="text/plain"),
        )
        content_md = response.text.strip()
    except Exception as exc:
        logger.warning("Wiki generation failed: %s", exc)
        return None

    # Extract title from first # heading
    title = source_hint
    for line in content_md.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Extract "Questions to Explore" as a list
    questions: list[str] = []
    in_questions = False
    for line in content_md.splitlines():
        if "Questions to Explore" in line:
            in_questions = True
            continue
        if in_questions:
            if line.startswith("## "):
                break
            stripped = line.strip()
            if stripped and stripped[0].isdigit() and ". " in stripped:
                questions.append(stripped.split(". ", 1)[1])

    wiki_page = {
        "job_id": job_id,
        "title": title,
        "content_md": content_md,
        "questions": questions,
        "entity_count": len(entities),
        "relationship_count": len(relationships),
        "source_hint": source_hint,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Store as WikiPage node in Neo4j
    if neo4j_client is not None and neo4j_client.available:
        try:
            await neo4j_client.execute_query(
                """
                MERGE (w:WikiPage {job_id: $job_id})
                SET w.title = $title,
                    w.content_md = $content_md,
                    w.questions = $questions,
                    w.entity_count = $entity_count,
                    w.relationship_count = $relationship_count,
                    w.source_hint = $source_hint,
                    w.generated_at = $generated_at
                """,
                {
                    "job_id": job_id,
                    "title": title,
                    "content_md": content_md,
                    "questions": json.dumps(questions),
                    "entity_count": len(entities),
                    "relationship_count": len(relationships),
                    "source_hint": source_hint,
                    "generated_at": wiki_page["generated_at"],
                },
            )
            # Link wiki page to its entity nodes
            for entity in entities[:20]:
                name = entity.get("name", "")
                if name:
                    await neo4j_client.execute_query(
                        """
                        MATCH (w:WikiPage {job_id: $job_id})
                        MATCH (n:KGNode {name: $name})
                        MERGE (w)-[:WIKI_COVERS]->(n)
                        """,
                        {"job_id": job_id, "name": name},
                    )
        except Exception as exc:
            logger.warning("Failed to store wiki page in Neo4j: %s", exc)

    return wiki_page
