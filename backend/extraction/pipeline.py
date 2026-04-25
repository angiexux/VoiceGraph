"""Three-phase knowledge-graph extraction pipeline.

Phase A -- Schema-Free Discovery: extract entities/relationships without constraints
Phase B -- Ontology Generation: build a formal OWL ontology from discovered types
Phase C -- Precision Extraction: re-extract using ontology constraints, write to Neo4j
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Callable, Awaitable

from .chunker import chunk_text
from .ontology_manager import OntologyManager
from .parsers import parse_document

logger = logging.getLogger(__name__)

# Type alias for the WebSocket event callback
EventCallback = Callable[[dict[str, Any]], Awaitable[None]] | None


# --------------------------------------------------------------------------
# Gemini client wrapper (works with or without API key)
# --------------------------------------------------------------------------

def _gemini_available() -> bool:
    """Check if a Gemini API key is configured."""
    return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))


async def _call_gemini(prompt: str, json_mode: bool = True) -> str:
    """Call Gemini 2.5 Flash and return the response text.

    Falls back to mock responses when no API key is available.
    """
    if not _gemini_available():
        return ""  # caller handles mock fallback

    try:
        from google import genai

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)

        config = None
        if json_mode:
            config = genai.types.GenerateContentConfig(
                response_mime_type="application/json",
            )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )
        return response.text
    except Exception as exc:
        logger.warning("Gemini API call failed: %s", exc)
        return ""


def _parse_json_response(text: str) -> dict | list | None:
    """Extract and parse JSON from an LLM response, handling markdown fences."""
    if not text:
        return None

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def _extract_turtle(text: str) -> str | None:
    """Extract Turtle content from an LLM response."""
    if not text:
        return None

    # Try extracting from code fence
    match = re.search(r"```(?:turtle|ttl)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If text contains @prefix, treat the whole thing as Turtle
    if "@prefix" in text:
        return text.strip()

    return None


# --------------------------------------------------------------------------
# Mock data for development without Gemini API key
# --------------------------------------------------------------------------

MOCK_ENTITIES = [
    {"name": "Machine Learning", "type": "Concept", "description": "A branch of artificial intelligence"},
    {"name": "Neural Network", "type": "Technology", "description": "Computing system inspired by biological neural networks"},
    {"name": "Deep Learning", "type": "Concept", "description": "Subset of machine learning using deep neural networks"},
    {"name": "GPT-4", "type": "Model", "description": "Large language model by OpenAI"},
    {"name": "Transformer", "type": "Architecture", "description": "Neural network architecture using attention mechanisms"},
    {"name": "OpenAI", "type": "Organization", "description": "AI research company"},
    {"name": "Google", "type": "Organization", "description": "Technology company"},
    {"name": "BERT", "type": "Model", "description": "Bidirectional encoder representations from transformers"},
    {"name": "Natural Language Processing", "type": "Concept", "description": "Field of AI for understanding human language"},
    {"name": "Computer Vision", "type": "Concept", "description": "Field of AI for understanding visual data"},
    {"name": "Attention Mechanism", "type": "Technology", "description": "Technique allowing models to focus on relevant input parts"},
    {"name": "Geoffrey Hinton", "type": "Person", "description": "Pioneer of deep learning"},
]

MOCK_RELATIONSHIPS = [
    {"source": "Deep Learning", "target": "Machine Learning", "type": "IS_SUBSET_OF", "description": "Deep learning is a subset of machine learning"},
    {"source": "Neural Network", "target": "Deep Learning", "type": "ENABLES", "description": "Neural networks enable deep learning"},
    {"source": "Transformer", "target": "Attention Mechanism", "type": "USES", "description": "Transformers use attention mechanisms"},
    {"source": "GPT-4", "target": "Transformer", "type": "BASED_ON", "description": "GPT-4 is based on transformer architecture"},
    {"source": "BERT", "target": "Transformer", "type": "BASED_ON", "description": "BERT is based on transformer architecture"},
    {"source": "OpenAI", "target": "GPT-4", "type": "DEVELOPED", "description": "OpenAI developed GPT-4"},
    {"source": "Google", "target": "BERT", "type": "DEVELOPED", "description": "Google developed BERT"},
    {"source": "Geoffrey Hinton", "target": "Deep Learning", "type": "PIONEERED", "description": "Geoffrey Hinton pioneered deep learning"},
    {"source": "Natural Language Processing", "target": "Machine Learning", "type": "IS_SUBSET_OF", "description": "NLP is a subset of machine learning"},
    {"source": "Computer Vision", "target": "Machine Learning", "type": "IS_SUBSET_OF", "description": "Computer vision is a subset of machine learning"},
    {"source": "GPT-4", "target": "Natural Language Processing", "type": "APPLIED_IN", "description": "GPT-4 is applied in NLP"},
]

MOCK_TURTLE = """@prefix vg: <http://voicegraph.ai/ontology/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

vg:Concept a owl:Class ;
    rdfs:label "Concept" ;
    rdfs:comment "An abstract concept or field of study" .

vg:Technology a owl:Class ;
    rdfs:label "Technology" ;
    rdfs:comment "A specific technology or technique" .

vg:Model a owl:Class ;
    rdfs:subClassOf vg:Technology ;
    rdfs:label "Model" ;
    rdfs:comment "An AI/ML model" .

vg:Architecture a owl:Class ;
    rdfs:subClassOf vg:Technology ;
    rdfs:label "Architecture" ;
    rdfs:comment "A system or model architecture" .

vg:Organization a owl:Class ;
    rdfs:label "Organization" ;
    rdfs:comment "A company or institution" .

vg:Person a owl:Class ;
    rdfs:label "Person" ;
    rdfs:comment "A human individual" .

vg:IS_SUBSET_OF a owl:ObjectProperty ;
    rdfs:label "IS_SUBSET_OF" ;
    rdfs:domain vg:Concept ;
    rdfs:range vg:Concept ;
    rdfs:comment "Indicates a concept is a subset of another" .

vg:ENABLES a owl:ObjectProperty ;
    rdfs:label "ENABLES" ;
    rdfs:domain vg:Technology ;
    rdfs:range vg:Concept ;
    rdfs:comment "A technology enables a concept or field" .

vg:USES a owl:ObjectProperty ;
    rdfs:label "USES" ;
    rdfs:domain vg:Technology ;
    rdfs:range vg:Technology ;
    rdfs:comment "One technology uses another" .

vg:BASED_ON a owl:ObjectProperty ;
    rdfs:label "BASED_ON" ;
    rdfs:domain vg:Model ;
    rdfs:range vg:Architecture ;
    rdfs:comment "A model is based on an architecture" .

vg:DEVELOPED a owl:ObjectProperty ;
    rdfs:label "DEVELOPED" ;
    rdfs:domain vg:Organization ;
    rdfs:range vg:Technology ;
    rdfs:comment "An organization developed a technology" .

vg:PIONEERED a owl:ObjectProperty ;
    rdfs:label "PIONEERED" ;
    rdfs:domain vg:Person ;
    rdfs:range vg:Concept ;
    rdfs:comment "A person pioneered a concept" .

vg:APPLIED_IN a owl:ObjectProperty ;
    rdfs:label "APPLIED_IN" ;
    rdfs:domain vg:Technology ;
    rdfs:range vg:Concept ;
    rdfs:comment "A technology is applied in a field" .
"""


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

class ExtractionPipeline:
    """Orchestrates the 3-phase extraction of a knowledge graph from
    unstructured sources (PDFs, YouTube transcripts, web pages, raw text).

    Usage::

        pipeline = ExtractionPipeline(neo4j_client=client, event_callback=ws_send)
        result = await pipeline.run("https://youtube.com/watch?v=...", "youtube")
    """

    def __init__(
        self,
        neo4j_client: Any = None,
        event_callback: EventCallback = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._neo4j = neo4j_client
        self._event_callback = event_callback
        # Metadata applied to every node and edge (collection_name, context, etc.)
        self._metadata = metadata or {}

    # ------------------------------------------------------------------
    # Event broadcasting
    # ------------------------------------------------------------------

    async def _emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Send a progress event via the callback if one is registered."""
        event = {"type": event_type, "timestamp": time.time(), **(data or {})}
        logger.info("Pipeline event: %s", event_type)
        if self._event_callback:
            try:
                await self._event_callback(event)
            except Exception as exc:
                logger.warning("Event callback failed: %s", exc)

    # ------------------------------------------------------------------
    # Phase A -- Schema-Free Discovery
    # ------------------------------------------------------------------

    async def run_phase_a(self, text: str) -> dict[str, Any]:
        """Extract entities and relationships without schema constraints.

        1. Chunk text into ~1000-token chunks with 200-token overlap.
        2. For each chunk, call Gemini to freely extract entities and
           relationships.
        3. Collect all discovered entity types and relationship types.
        4. Send progress events via callback.

        Args:
            text: Full document text.

        Returns:
            A dict with ``entities``, ``relationships``, and
            ``discovered_types``.
        """
        await self._emit("phase_a_start", {"status": "Discovering entities..."})

        # Use larger chunks for speed — fewer API calls
        chunks = chunk_text(text, chunk_size=3000, overlap=200)
        if not chunks:
            chunks = [text] if text else []

        all_entities: list[dict[str, Any]] = []
        all_relationships: list[dict[str, Any]] = []

        use_mock = not _gemini_available()
        if use_mock:
            logger.info("No Gemini API key found -- using mock extraction data")

        for i, chunk in enumerate(chunks):
            await self._emit("phase_a_progress", {
                "status": f"Analyzing chunk {i + 1}/{len(chunks)}...",
                "progress": (i + 1) / len(chunks),
                "chunk": i + 1,
                "total_chunks": len(chunks),
            })

            if use_mock:
                # Use mock data scaled to the number of chunks
                if i == 0:
                    all_entities.extend(MOCK_ENTITIES)
                    all_relationships.extend(MOCK_RELATIONSHIPS)
                continue

            prompt = f"""Extract all entities and relationships from this text.
Return valid JSON with this exact structure:
{{
  "entities": [
    {{"name": "entity name", "type": "EntityType", "description": "brief description"}}
  ],
  "relationships": [
    {{"source": "entity1 name", "target": "entity2 name", "type": "RELATIONSHIP_TYPE", "description": "brief description"}}
  ]
}}

TEXT:
{chunk}"""

            response_text = await _call_gemini(prompt, json_mode=True)
            parsed = _parse_json_response(response_text)

            if parsed and isinstance(parsed, dict):
                entities = parsed.get("entities", [])
                relationships = parsed.get("relationships", [])
                all_entities.extend(entities)
                all_relationships.extend(relationships)

                # Emit each discovered entity as an event
                for entity in entities:
                    await self._emit("entity_discovered", {
                        "entity": entity,
                        "phase": "A",
                    })

        # Collect discovered types
        entity_types: dict[str, int] = {}
        for e in all_entities:
            t = e.get("type", "Unknown")
            entity_types[t] = entity_types.get(t, 0) + 1

        relationship_types: dict[str, int] = {}
        for r in all_relationships:
            t = r.get("type", "RELATED_TO")
            relationship_types[t] = relationship_types.get(t, 0) + 1

        discovered_types = {
            "entity_types": entity_types,
            "relationship_types": relationship_types,
        }

        await self._emit("phase_a_complete", {
            "status": f"Discovered {len(all_entities)} entities, "
                      f"{len(all_relationships)} relationships",
            "entity_count": len(all_entities),
            "relationship_count": len(all_relationships),
            "discovered_types": discovered_types,
        })

        return {
            "entities": all_entities,
            "relationships": all_relationships,
            "discovered_types": discovered_types,
        }

    # ------------------------------------------------------------------
    # Fast write — skip Phase B/C, write Phase A results directly
    # ------------------------------------------------------------------

    async def _write_phase_a_results(self, discovery: dict[str, Any]) -> dict[str, Any]:
        """Write Phase A discovery results directly to Neo4j, skipping ontology."""
        await self._emit("phase_c_start", {"status": "Writing to graph..."})

        entities = discovery["entities"]
        relationships = discovery["relationships"]

        # Improved entity resolution with fuzzy matching
        try:
            from extraction.entity_resolution import resolve_entities
            domain = self._metadata.get("domain", "")
            source_type = self._metadata.get("source_type", "text")
            unique_entities = resolve_entities(entities, domain=domain, source_type=source_type)
        except ImportError:
            logger.warning("entity_resolution not available, falling back to simple dedup")
            seen: dict[str, dict[str, Any]] = {}
            for e in entities:
                name = e.get("name", "")
                if name and name not in seen:
                    seen[name] = e
            unique_entities = list(seen.values())

        nodes_created = 0
        edges_created = 0

        if self._neo4j is not None:
            try:
                nodes_created = await self._write_nodes(unique_entities)
                # Signal frontend to refresh graph after nodes are written
                await self._emit("graph_refresh", {"reason": "nodes_written", "count": nodes_created})
                edges_created = await self._write_edges(relationships)
                # Signal again after edges
                await self._emit("graph_refresh", {"reason": "edges_written", "count": edges_created})
            except Exception as exc:
                logger.error("Failed to write to Neo4j: %s", exc)

        stats = {
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "total_entities": len(unique_entities),
            "total_relationships": len(relationships),
            "chunks_processed": 1,
        }

        await self._emit("phase_c_complete", {
            "status": f"Done: {len(unique_entities)} entities, {len(relationships)} relationships",
            **stats,
        })

        return stats

    # ------------------------------------------------------------------
    # Phase B -- Ontology Generation
    # ------------------------------------------------------------------

    async def run_phase_b(
        self,
        discovered_types: dict[str, Any],
        sample_text: str,
    ) -> OntologyManager:
        """Generate a formal OWL ontology from the discovered types.

        1. Send discovered types + sample text to Gemini.
        2. Parse generated Turtle with OntologyManager.
        3. Validate the ontology.

        Args:
            discovered_types: Dict with ``entity_types`` and
                ``relationship_types`` counts from Phase A.
            sample_text: A sample of the source text for context.

        Returns:
            A populated OntologyManager.
        """
        await self._emit("phase_b_start", {"status": "Generating ontology..."})

        ontology = OntologyManager()
        use_mock = not _gemini_available()

        if use_mock:
            logger.info("No Gemini API key -- using mock ontology")
            import tempfile
            ttl_path = os.path.join(tempfile.gettempdir(), "voicegraph_mock.ttl")
            with open(ttl_path, "w") as f:
                f.write(MOCK_TURTLE)
            ontology.load_from_turtle(ttl_path)
        else:
            entity_types = discovered_types.get("entity_types", {})
            relationship_types = discovered_types.get("relationship_types", {})

            prompt = f"""Given these discovered entity types and relationships from a document,
generate a formal OWL ontology in Turtle (.ttl) format.

DISCOVERED ENTITY TYPES (with counts):
{json.dumps(entity_types, indent=2)}

DISCOVERED RELATIONSHIP TYPES (with counts):
{json.dumps(relationship_types, indent=2)}

SAMPLE TEXT FROM DOCUMENT:
{sample_text[:2000]}

REQUIREMENTS:
1. Use namespace prefix: @prefix vg: <http://voicegraph.ai/ontology/> .
2. Consolidate similar entity types into a clean class hierarchy.
3. Define all classes as owl:Class with rdfs:label and rdfs:comment.
4. Use rdfs:subClassOf for class hierarchy where appropriate.
5. Define all relationship types as owl:ObjectProperty with rdfs:domain and rdfs:range.
6. Every ObjectProperty MUST have both domain and range set.
7. Add rdfs:label and rdfs:comment to every property.
8. Output ONLY the Turtle content, no explanatory text.

Generate the complete Turtle ontology:"""

            response_text = await _call_gemini(prompt, json_mode=False)
            turtle_content = _extract_turtle(response_text)

            if turtle_content:
                try:
                    import tempfile
                    ttl_path = os.path.join(tempfile.gettempdir(), "voicegraph_generated.ttl")
                    with open(ttl_path, "w") as f:
                        f.write(turtle_content)
                    ontology.load_from_turtle(ttl_path)
                except Exception as exc:
                    logger.warning("Failed to parse generated Turtle: %s", exc)
                    # Fall back to building ontology from discovered types
                    ontology = self._build_ontology_from_types(discovered_types)
            else:
                logger.warning("No Turtle content in Gemini response, building from types")
                ontology = self._build_ontology_from_types(discovered_types)

        # Validate
        validation = ontology.validate()
        if not validation["valid"]:
            logger.warning("Ontology validation errors: %s", validation["errors"])

        schema = ontology.to_graph_schema()
        await self._emit("phase_b_complete", {
            "status": f"Ontology generated: {len(schema['node_types'])} node types, "
                      f"{len(schema['relationship_types'])} relationship types",
            "node_types": len(schema["node_types"]),
            "relationship_types": len(schema["relationship_types"]),
            "validation": validation,
        })

        return ontology

    def _build_ontology_from_types(
        self, discovered_types: dict[str, Any]
    ) -> OntologyManager:
        """Fallback: build an ontology directly from discovered types without LLM."""
        ontology = OntologyManager()

        entity_types = discovered_types.get("entity_types", {})
        relationship_types = discovered_types.get("relationship_types", {})

        # Add all entity types as classes
        for type_name in entity_types:
            clean_name = re.sub(r"[^a-zA-Z0-9_]", "", type_name.replace(" ", "_"))
            if clean_name:
                ontology.add_class(clean_name, description=f"Discovered type: {type_name}")

        # Add relationship types as object properties
        # Without LLM guidance, use generic domain/range
        class_names = [
            re.sub(r"[^a-zA-Z0-9_]", "", t.replace(" ", "_"))
            for t in entity_types
        ]
        if not class_names:
            class_names = ["Entity"]
            ontology.add_class("Entity", description="Generic entity")

        for rel_type in relationship_types:
            clean_name = re.sub(r"[^a-zA-Z0-9_]", "", rel_type.replace(" ", "_"))
            if clean_name:
                ontology.add_object_property(
                    clean_name,
                    domain=class_names[0],
                    range=class_names[0],
                    description=f"Discovered relationship: {rel_type}",
                )

        return ontology

    # ------------------------------------------------------------------
    # Phase C -- Precision Extraction
    # ------------------------------------------------------------------

    async def run_phase_c(
        self,
        text: str,
        ontology: OntologyManager,
    ) -> dict[str, Any]:
        """Re-extract entities and relationships constrained by the ontology.

        1. Get ontology as JSON (classes + properties).
        2. Chunk text again.
        3. For each chunk, call Gemini with ontology constraints.
        4. Write results to Neo4j via the client.
        5. Send progress events.

        Args:
            text: Full document text.
            ontology: The validated OntologyManager from Phase B.

        Returns:
            A dict with extraction stats.
        """
        await self._emit("phase_c_start", {"status": "Precision extraction..."})

        schema = ontology.to_graph_schema()
        ontology_json = ontology.to_json()
        chunks = chunk_text(text, chunk_size=1000, overlap=200)
        if not chunks:
            chunks = [text] if text else []

        # Build the allowed types lists for the prompt
        class_names = [nt["label"] for nt in schema["node_types"]]
        rel_names = [rt["label"] for rt in schema["relationship_types"]]
        patterns = schema.get("patterns", [])

        all_entities: list[dict[str, Any]] = []
        all_relationships: list[dict[str, Any]] = []

        use_mock = not _gemini_available()

        for i, chunk in enumerate(chunks):
            await self._emit("phase_c_progress", {
                "status": f"Extracting chunk {i + 1}/{len(chunks)}...",
                "progress": (i + 1) / len(chunks),
            })

            if use_mock:
                if i == 0:
                    all_entities.extend(MOCK_ENTITIES)
                    all_relationships.extend(MOCK_RELATIONSHIPS)
                continue

            patterns_str = "\n".join(
                f"  - {p['source']} --[{p['relationship']}]--> {p['target']}"
                for p in patterns
            )

            prompt = f"""Extract entities and relationships from this text using ONLY the types defined below.

ALLOWED ENTITY TYPES: {json.dumps(class_names)}
ALLOWED RELATIONSHIP TYPES: {json.dumps(rel_names)}

VALID RELATIONSHIP PATTERNS:
{patterns_str}

RULES:
- You may ONLY use the entity types listed above.
- You may ONLY use the relationship types listed above.
- Each relationship must follow one of the valid patterns above.
- If an entity does not fit any allowed type, skip it.
- Return valid JSON.

Return this exact JSON structure:
{{
  "entities": [
    {{"name": "entity name", "type": "AllowedEntityType", "description": "brief description"}}
  ],
  "relationships": [
    {{"source": "entity1 name", "target": "entity2 name", "type": "ALLOWED_REL_TYPE", "description": "brief description"}}
  ]
}}

TEXT:
{chunk}"""

            response_text = await _call_gemini(prompt, json_mode=True)
            parsed = _parse_json_response(response_text)

            if parsed and isinstance(parsed, dict):
                entities = parsed.get("entities", [])
                relationships = parsed.get("relationships", [])

                # Filter to allowed types only if we have a well-formed ontology
                # If ontology generation failed, accept everything Gemini gives us
                if class_names and len(class_names) > 2:
                    entities = [
                        e for e in entities
                        if e.get("type") in class_names
                    ]
                if rel_names and len(rel_names) > 2:
                    relationships = [
                        r for r in relationships
                        if r.get("type") in rel_names
                    ]

                all_entities.extend(entities)
                all_relationships.extend(relationships)

                for entity in entities:
                    await self._emit("node_added", {
                        "entity": entity,
                        "phase": "C",
                    })

        # Deduplicate entities by name (keep first occurrence)
        seen_entities: dict[str, dict[str, Any]] = {}
        for e in all_entities:
            name = e.get("name", "")
            if name and name not in seen_entities:
                seen_entities[name] = e
        unique_entities = list(seen_entities.values())

        # Write to Neo4j
        nodes_created = 0
        edges_created = 0

        if self._neo4j is not None:
            try:
                nodes_created = await self._write_nodes(unique_entities)
                edges_created = await self._write_edges(all_relationships)
            except Exception as exc:
                logger.error("Failed to write to Neo4j: %s", exc)

        stats = {
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "total_entities": len(unique_entities),
            "total_relationships": len(all_relationships),
            "chunks_processed": len(chunks),
        }

        await self._emit("phase_c_complete", {
            "status": f"Extraction complete: {len(unique_entities)} entities, "
                      f"{len(all_relationships)} relationships",
            **stats,
        })

        return stats

    # ------------------------------------------------------------------
    # Neo4j write helpers
    # ------------------------------------------------------------------

    async def _write_nodes(self, entities: list[dict[str, Any]]) -> int:
        """Write entity nodes to Neo4j.

        Args:
            entities: List of entity dicts with ``name``, ``type``,
                ``description``.

        Returns:
            Number of nodes created.
        """
        if self._neo4j is None:
            return 0

        count = 0
        for entity in entities:
            name = entity.get("name", "")
            entity_type = entity.get("type", "Entity")
            description = entity.get("description", "")

            # Sanitise the label for Neo4j (must be a valid identifier)
            label = re.sub(r"[^a-zA-Z0-9_]", "", entity_type.replace(" ", "_"))
            if not label:
                label = "Entity"

            params = {
                "name": name, "description": description, "entity_type": entity_type,
                "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source_type": self._metadata.get("source_type", "text"),
                "collection_name": self._metadata.get("collection_name", ""),
                "context": self._metadata.get("context", "personal"),
                "document_created_at": self._metadata.get("document_created_at", ""),
            }
            cypher = (
                f"MERGE (n:{label} {{name: $name}}) "
                f"SET n.description = $description, n.entity_type = $entity_type, "
                f"n.ingested_at = $ingested_at, n.source_type = $source_type, "
                f"n.collection_name = $collection_name, n.context = $context, "
                f"n.document_created_at = $document_created_at "
                f"RETURN n"
            )
            try:
                await self._neo4j.execute_query(cypher, params)
                count += 1
            except Exception as exc:
                logger.warning("Failed to create node '%s': %s", name, exc)

        return count

    async def _write_edges(self, relationships: list[dict[str, Any]]) -> int:
        """Write relationship edges to Neo4j.

        Args:
            relationships: List of relationship dicts with ``source``,
                ``target``, ``type``, ``description``.

        Returns:
            Number of edges created.
        """
        if self._neo4j is None:
            return 0

        count = 0
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "RELATED_TO")
            description = rel.get("description", "")

            # Sanitise the relationship type for Neo4j
            rel_label = re.sub(r"[^a-zA-Z0-9_]", "", rel_type.replace(" ", "_"))
            if not rel_label:
                rel_label = "RELATED_TO"

            params = {
                "source": source, "target": target, "description": description,
                "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source_type": self._metadata.get("source_type", "text"),
                "collection_name": self._metadata.get("collection_name", ""),
                "context": self._metadata.get("context", "personal"),
                "document_created_at": self._metadata.get("document_created_at", ""),
            }
            cypher = (
                f"MATCH (a {{name: $source}}), (b {{name: $target}}) "
                f"MERGE (a)-[r:{rel_label}]->(b) "
                f"SET r.description = $description, "
                f"r.ingested_at = $ingested_at, r.source_type = $source_type, "
                f"r.collection_name = $collection_name, r.context = $context, "
                f"r.document_created_at = $document_created_at "
                f"RETURN r"
            )
            try:
                await self._neo4j.execute_query(cypher, params)
                count += 1
            except Exception as exc:
                logger.warning(
                    "Failed to create edge '%s' -[%s]-> '%s': %s",
                    source, rel_type, target, exc,
                )

        return count

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    async def run(
        self,
        source: str,
        source_type: str = "auto",
    ) -> dict[str, Any]:
        """Execute the full A -> B -> C pipeline.

        Args:
            source: File path, URL, or raw text.
            source_type: One of ``pdf``, ``url``, ``youtube``, ``text``,
                ``markdown``, or ``auto``.

        Returns:
            A summary dict with results from all three phases.
        """
        start_time = time.time()
        await self._emit("pipeline_start", {
            "status": "Starting extraction pipeline...",
            "source": source[:200],
            "source_type": source_type,
        })

        try:
            # Parse document
            await self._emit("parsing_start", {"status": "Parsing document..."})
            text = await parse_document(source, source_type)
            await self._emit("parsing_complete", {
                "status": f"Parsed {len(text)} characters",
                "character_count": len(text),
            })

            if not text.strip():
                await self._emit("pipeline_error", {
                    "status": "No text content extracted from source",
                })
                return {
                    "error": "No text content extracted from source",
                    "phase_a": None,
                    "phase_b": None,
                    "phase_c": None,
                }

            # Single-phase fast extraction — extract and write directly
            discovery = await self.run_phase_a(text)

            # Skip Phase B/C for speed — write Phase A results directly to Neo4j
            results = await self._write_phase_a_results(discovery)

            elapsed = time.time() - start_time
            summary = {
                "phase_a": {
                    "entities_discovered": len(discovery["entities"]),
                    "relationships_discovered": len(discovery["relationships"]),
                    "types_discovered": discovery["discovered_types"],
                },
                "phase_b": None,
                "phase_c": results,
                "elapsed_seconds": round(elapsed, 2),
            }

            await self._emit("pipeline_complete", {
                "status": f"Pipeline complete in {elapsed:.1f}s: "
                          f"{results['total_entities']} entities, "
                          f"{results['total_relationships']} relationships",
                "summary": summary,
            })

            return summary

        except Exception as exc:
            logger.error("Pipeline failed: %s", exc, exc_info=True)
            await self._emit("pipeline_error", {
                "status": f"Pipeline failed: {exc}",
                "error": str(exc),
            })
            return {
                "error": str(exc),
                "phase_a": None,
                "phase_b": None,
                "phase_c": None,
            }
