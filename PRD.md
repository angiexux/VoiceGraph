# Technical PRD v2: VoiceGraph — Voice-First Interactive Knowledge Graph

## Product Vision

A voice-first knowledge graph platform where users ingest multimodal data (PDFs, text, audio, video, YouTube, URLs, CSVs), the system automatically builds a deep ontology-guided knowledge graph using a 3-phase extraction pipeline (Discovery → Ontology Generation → Precision Extraction), and users explore/analyze/build/refine the graph through natural voice conversation powered by Gemini Live — with agentic GraphRAG querying that truly understands the underlying graph structure — all rendered as a beautiful, interactive, real-time 3D graph.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Reagraph 3D │  │  Voice UI    │  │  Canvas (V1.1)         │ │
│  │  Graph Viz   │  │  Controls    │  │  React live rendering  │ │
│  │  + Highlight │  │  + Waveform  │  │  explanations/flows    │ │
│  └──────┬───────┘  └──────┬───────┘  └────────────────────────┘ │
│         │                 │                                      │
│         └────────┬────────┘                                      │
│                  │ WebSocket                                     │
└──────────────────┼───────────────────────────────────────────────┘
                   │
┌──────────────────┼───────────────────────────────────────────────┐
│                  │     BACKEND (Python FastAPI on Cloud Run)     │
│                  │                                               │
│  ┌───────────────▼───────────────┐                               │
│  │   WebSocket Gateway           │                               │
│  │   (audio + events + graph)    │                               │
│  └───────────────┬───────────────┘                               │
│                  │                                               │
│  ┌───────────────▼───────────────┐                               │
│  │   ADK Orchestrator Agent      │                               │
│  │   (Gemini Live + Functions)   │                               │
│  │                               │                               │
│  │   Sub-agents:                 │  ┌─────────────────────────┐  │
│  │   ├── GraphQueryAgent ────────┼──┤  Neo4j AuraDB Free      │  │
│  │   │   (Agentic GraphRAG)      │  │  (Graph + Vector Store) │  │
│  │   ├── DataIngestionAgent      │  └─────────────────────────┘  │
│  │   │   (neo4j-graphrag lib)    │                               │
│  │   ├── OntologyAgent           │  ┌─────────────────────────┐  │
│  │   │   (Voice ontology edit)   │  │  Cloud Storage (GCS)    │  │
│  │   ├── CSVAnalysisAgent        │  │  (Source files, ontology │  │
│  │   │   (Auto schema detect)    │  │   backups, exports)     │  │
│  │   └── ExplanationAgent        │  └─────────────────────────┘  │
│  └───────────────────────────────┘                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  3-Phase Extraction Pipeline                                 ││
│  │  (neo4j-graphrag lib + TrustGraph ontology patterns)         ││
│  │                                                              ││
│  │  Phase A ──► Phase B ──► Phase C ──► Entity Resolution       ││
│  │  Schema-free  Ontology    Precision   (Exact + Fuzzy +       ││
│  │  Discovery    Generation  Extraction   Semantic dedup)       ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack (Final)

| Layer | Technology | Why |
|---|---|---|
| **Voice AI** | Gemini Live (Multimodal Live API) | Real-time bidirectional voice, function calling mid-conversation, camera/screen vision |
| **Agent Framework** | Google ADK (Python) | Required by hackathon, multi-agent orchestration, Cloud Run deploy |
| **Graph Database** | Neo4j AuraDB Free | $0, instant setup, 200K nodes/400K rels, mature Cypher, runs on GCP infra |
| **KG Builder Library** | `neo4j-graphrag[google]` | Official Neo4j library — handles chunking, extraction, entity resolution, writing, retrievers |
| **Ontology Management** | `rdflib` + custom JSON | Lightweight OWL manipulation (no Java), Turtle serialization, agent-friendly JSON format |
| **Graph Visualization** | Reagraph | React-native, 3D, built-in selections/highlighting, modern aesthetic |
| **Frontend** | React 18 + TypeScript + Vite | Standard, fast, great DX |
| **Backend** | Python FastAPI + WebSocket | Async, fast, ADK-compatible |
| **Extraction LLM** | Gemini 2.5 Flash via `VertexAILLM` | Fast, cheap, multimodal, required by hackathon |
| **Hosting** | Google Cloud Run | Serverless, auto-scales, `adk deploy cloud_run` |
| **File Storage** | Google Cloud Storage | Source files, audio, video |
| **Embeddings** | Gemini Embedding API | Google-native, good quality |
| **Styling** | Tailwind CSS + shadcn/ui | Clean, modern, fast to build |

### Open Source Code We're Reusing

| Source Repo | License | What We Take |
|---|---|---|
| **`neo4j/neo4j-graphrag-python`** | Apache 2.0 | `SimpleKGPipeline`, `LLMEntityRelationExtractor`, `VertexAILLM`, all Retrievers, Entity Resolution, `GraphSchema`, `SchemaFromTextExtractor` |
| **`trustgraph-ai/trustgraph`** | Apache 2.0 | Ontology-guided extraction pattern (vector-embed OWL classes → find relevant subset per chunk → constrain LLM), provenance tracking approach, ReAct agent query patterns |
| **`neo4j-labs/llm-graph-builder`** | MIT | YouTube transcript extraction pattern (`youtube_transcript_api`), web page scraping pattern, LLM-based schema consolidation, multi-mode chat retrieval architecture |

---

## Data Flow: Ingestion to Graph (3-Phase Pipeline)

This is the core intelligence of the system. We use the `neo4j-graphrag` library as the pipeline engine and overlay TrustGraph's ontology-guided approach on top.

```
User uploads file/URL/YouTube/CSV
        │
        ▼
┌─────────────────────────────────────┐
│  0. MULTIMODAL PRE-PROCESSING       │
│                                     │
│  PDF → neo4j-graphrag PdfLoader     │
│  Text/MD → direct text input        │
│  Audio → Gemini multimodal API      │
│         (native audio → text)       │
│  Video → Gemini multimodal API      │
│         (frames + audio → text)     │
│  YouTube → youtube_transcript_api   │
│           (stolen from llm-graph-   │
│            builder pattern)         │
│  URL → WebBaseLoader / BeautifulSoup│
│  CSV → CSVAnalysisAgent             │
│        (see CSV section below)      │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE A: SCHEMA-FREE DISCOVERY                                 │
│                                                                 │
│  neo4j-graphrag SimpleKGPipeline(schema="FREE")                 │
│                                                                 │
│  1. FixedSizeSplitter chunks text (~1000 tokens, 200 overlap)   │
│  2. LLMEntityRelationExtractor w/ VertexAILLM (Gemini Flash)    │
│     → LLM freely discovers entities and relationships           │
│     → No constraints, maximum coverage                          │
│  3. KGWriter writes discovered graph to Neo4j                   │
│  4. SchemaFromExistingGraphExtractor analyzes what was found     │
│     → Returns discovered node types, relationship types,        │
│       property patterns, frequency distribution                 │
│                                                                 │
│  Output: Raw discovered schema + populated graph                │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE B: ONTOLOGY GENERATION                                   │
│                                                                 │
│  Input: Phase A schema + source data sample + user context      │
│                                                                 │
│  1. Feed to Gemini with ontology generation prompt:             │
│     "Given these discovered entity types and relationships,     │
│      generate a formal OWL ontology in Turtle format.           │
│      Consolidate similar types, define proper class hierarchy,  │
│      set domain/range on all properties, add descriptions."     │
│                                                                 │
│  2. Parse generated Turtle with rdflib → validate structure     │
│                                                                 │
│  3. Convert OWL → neo4j-graphrag GraphSchema format:            │
│     owl:Class → NodeType(label, properties, description)        │
│     owl:ObjectProperty → RelationshipType + Pattern             │
│     owl:DatatypeProperty → PropertyType on NodeType             │
│                                                                 │
│  4. Store ontology as JSON (agent-editable) + Turtle (canonical)│
│                                                                 │
│  5. Voice checkpoint: Agent narrates the generated ontology     │
│     "I've identified 8 entity types and 15 relationships.       │
│      The main entities are Person, Organization, Project..."    │
│     User can refine via voice (see OntologyAgent section)       │
│                                                                 │
│  Output: Validated OWL ontology + GraphSchema for Phase C       │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE C: PRECISION EXTRACTION                                  │
│  (TrustGraph-inspired ontology-guided approach)                 │
│                                                                 │
│  1. Clear Phase A's raw graph from Neo4j                        │
│     (keep source Document/Chunk nodes)                          │
│                                                                 │
│  2. For each text chunk:                                        │
│     a. ONTOLOGY SUBSETTING (TrustGraph pattern):                │
│        - All OWL classes + properties are embedded as vectors   │
│        - Vector similarity finds the 5-10 most relevant         │
│          ontology classes for THIS specific chunk                │
│        - Only the relevant ontology subset is sent to the LLM   │
│        - This keeps prompts small even with large ontologies    │
│                                                                 │
│     b. CONSTRAINED EXTRACTION:                                  │
│        neo4j-graphrag SimpleKGPipeline(schema=GraphSchema)      │
│        with additional_node_types=False                         │
│        with additional_relationship_types=False                 │
│        → LLM can ONLY extract entities matching OWL classes     │
│        → LLM can ONLY extract relationships matching properties │
│        → Each extraction includes confidence + source chunk ref │
│                                                                 │
│  3. Entity Resolution (neo4j-graphrag built-in):                │
│     a. SinglePropertyExactMatchResolver (fast, free)            │
│     b. FuzzyMatchResolver (rapidfuzz, similarity_threshold=0.8) │
│     c. LLM-based schema consolidation                          │
│        (stolen from llm-graph-builder post-processing)          │
│                                                                 │
│  4. Provenance tracking:                                        │
│     Every entity node gets:                                     │
│     - source_document: which file it came from                  │
│     - source_chunk: which text chunk                            │
│     - extraction_confidence: LLM confidence score               │
│     - extraction_phase: "precision" (vs "discovery")            │
│     Every relationship gets same provenance properties           │
│                                                                 │
│  5. Vector embeddings created for all entity nodes               │
│     (for semantic search in agentic querying)                   │
│                                                                 │
│  Output: Clean, ontology-conformant, deduplicated knowledge     │
│          graph with full provenance                             │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Architecture Works

- **Phase A** catches everything — no entity type is missed because there are no constraints
- **Phase B** uses the LLM to impose human-quality semantic structure on the raw findings
- **Phase C** re-extracts with precision — consistent labels, proper types, no drift
- **Ontology subsetting** (from TrustGraph) means this scales to large ontologies without blowing context windows
- **Entity resolution** (from neo4j-graphrag) handles deduplication automatically
- **All of this uses pre-built libraries** — we write orchestration code, not extraction code

---

## CSV → Smart Auto-Detection Pipeline

When a CSV is uploaded, instead of treating it as text, the CSVAnalysisAgent handles it:

```
CSV File uploaded
        │
        ▼
┌───────────────────────────────────────────────┐
│  Stage 0: STATISTICAL PROFILING                │
│                                               │
│  pandas + ydata-profiling:                    │
│  - Column data types (int, float, str, date)  │
│  - Cardinality (unique value counts)          │
│  - Null rates per column                      │
│  - Value distributions                        │
│  - Sample rows (first 10)                     │
└─────────┬─────────────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────────────┐
│  Stage 1: HEURISTIC PRE-CLASSIFICATION        │
│  (Python rules, <5ms, no LLM cost)           │
│                                               │
│  - ID column detection: *_id, id_*, UUID      │
│  - FK candidate detection: value overlap      │
│    between columns across files               │
│  - Entity type extraction from column names   │
│  - Relationship pattern detection:            │
│    source/target, parent/child, from/to       │
│  - Score: graph_score, relational_score,      │
│           document_score (each 0-1)           │
└─────────┬─────────────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────────────┐
│  Stage 2: GEMINI ANALYSIS                      │
│                                               │
│  Send to Gemini Flash:                        │
│  - Headers + sample rows + Stage 0 stats      │
│  - Stage 1 heuristic scores                   │
│  - User's described use case (if provided)    │
│                                               │
│  Gemini returns:                              │
│  {                                            │
│    "recommendation": "graph" | "relational"   │
│                      | "document",            │
│    "confidence": 0.87,                        │
│    "reasoning": "Multiple entity types...",   │
│    "schema": { ... }  // Cypher or DDL        │
│  }                                            │
└─────────┬─────────────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────────────┐
│  Stage 3: SCHEMA GENERATION & IMPORT           │
│                                               │
│  If GRAPH:                                    │
│  - Generate Cypher LOAD CSV + MERGE statements│
│  - Create node types matching ontology classes │
│  - Create relationship types matching props   │
│  - Execute against Neo4j AuraDB               │
│  - Merge with existing ontology               │
│                                               │
│  If RELATIONAL:                               │
│  - Create SQLite DB (lightweight, in-process) │
│  - Generate CREATE TABLE with proper types,   │
│    PRIMARY KEY, FOREIGN KEY, indexes          │
│  - Load CSV data                              │
│  - Also create a "bridge" node in Neo4j       │
│    that links to the SQLite data for          │
│    graph-level awareness                      │
│                                               │
│  If DOCUMENT:                                 │
│  - Store as JSON documents in GCS             │
│  - Create summary node in Neo4j with          │
│    metadata + link to GCS location            │
└───────────────────────────────────────────────┘
```

### CSVAnalysisAgent (ADK)

```python
csv_analysis_agent = Agent(
    name="CSVAnalysisAgent",
    model="gemini-2.5-flash",
    description="Analyzes CSV files to auto-detect optimal storage structure",
    instruction="""You analyze CSV data to determine whether it should be stored as
    a graph (Neo4j), relational database (SQLite), or document store.
    Always explain your reasoning to the user via voice.
    After analysis, execute the import automatically.""",
    tools=[
        profile_csv,           # Run pandas + ydata-profiling
        heuristic_classify,    # Run Python heuristic rules
        generate_graph_schema, # Generate Cypher LOAD CSV
        generate_relational_schema, # Generate SQLite DDL
        execute_csv_import,    # Run the actual import
        merge_with_ontology,   # Update OWL ontology with new types from CSV
    ]
)
```

---

## Agentic GraphRAG Querying

This is the intelligence layer for answering questions. Instead of basic semantic search, the agent has a toolkit of specialized graph query strategies and dynamically selects the right one based on the question.

### Query Tool Arsenal

```python
# Tool 1: SEMANTIC CONCEPT SEARCH
# Use: "What do we know about climate change?"
# How: Vector similarity on entity embeddings
def search_concepts(query: str, top_k: int = 10) -> dict:
    """Semantic search across all entities in the knowledge graph.
    Uses vector embeddings to find conceptually similar entities.
    Returns matching entities with similarity scores."""
    # Uses neo4j-graphrag VectorRetriever
    # Vector index on entity node embeddings
    pass

# Tool 2: ENTITY EXPLORATION (1-2 hop neighborhood)
# Use: "Tell me about OpenAI" → returns full neighborhood
# How: Pre-built Cypher template, NOT Text2Cypher (faster + reliable)
def explore_entity(entity_name: str, depth: int = 2) -> dict:
    """Get the full neighborhood of an entity — all connected nodes
    and relationships up to N hops away. Use this to understand
    what an entity is connected to."""
    # MATCH (n {name: $name})-[r*1..$depth]-(m)
    # RETURN n, r, m
    pass

# Tool 3: PATH FINDING
# Use: "How does X relate to Y?"
# How: Pre-built Cypher template for shortest path
def find_path(entity_a: str, entity_b: str, max_hops: int = 5) -> dict:
    """Find the shortest path between two entities in the graph.
    Shows how two concepts are connected through intermediate entities.
    Returns the full path with all nodes and relationships."""
    # MATCH path = shortestPath((a {name: $a})-[*1..$max]-(b {name: $b}))
    # RETURN path
    pass

# Tool 4: DYNAMIC CYPHER (Text2Cypher — for complex queries)
# Use: "Which people work at organizations founded after 2020?"
# How: LLM generates Cypher from natural language + schema context
def query_graph(question: str) -> dict:
    """For complex analytical questions that require custom graph queries.
    Translates natural language to Cypher using the current graph schema.
    Use this when other tools are insufficient for the question's complexity."""
    # Uses neo4j-graphrag Text2CypherRetriever
    # Sends graph schema + few-shot examples + question to Gemini
    # Gemini generates Cypher → execute → return results
    pass

# Tool 5: HYBRID RETRIEVAL (Vector + Graph traversal)
# Use: "Summarize what we know about AI safety research"
# How: Vector search finds anchor nodes → Cypher expands context
def deep_search(query: str, top_k: int = 5, expansion_depth: int = 1) -> dict:
    """Deep search combining semantic similarity with graph traversal.
    First finds relevant entities via vector search, then expands
    their graph neighborhoods for rich context. Best for questions
    that need both semantic matching and structural understanding."""
    # Uses neo4j-graphrag VectorCypherRetriever
    # Step 1: Vector similarity → top K anchor entities
    # Step 2: For each anchor, Cypher traversal to get context
    # Step 3: Combine and rank results
    pass

# Tool 6: COMMUNITY/GLOBAL OVERVIEW
# Use: "What are the main themes in this data?"
# How: Leiden community detection + LLM summaries (from llm-graph-builder)
def get_communities(level: str = "top") -> dict:
    """Get high-level thematic summaries of the knowledge graph.
    Uses community detection to identify clusters of related entities
    and provides LLM-generated summaries of each community.
    Use this for 'big picture' questions about the data."""
    pass

# Tool 7: ONTOLOGY AWARENESS
# Use: "What types of entities do we have?"
# How: Read current OWL ontology
def get_ontology_info() -> dict:
    """Get the current ontology structure — all entity types,
    relationship types, their hierarchy, domain/range constraints.
    Use this to understand what the graph schema looks like."""
    pass

# Tool 8: GRAPH STATISTICS
# Use: "How big is the graph?"
def get_graph_stats() -> dict:
    """Get statistics about the knowledge graph — number of nodes,
    edges, entity type distribution, most connected entities,
    recent additions."""
    pass
```

### How the Agent Decides Which Tool to Use

The Orchestrator agent's instruction includes a decision framework:

```python
orchestrator = Agent(
    name="VoiceGraphOrchestrator",
    model="gemini-2.5-flash",
    instruction="""You are VoiceGraph, a voice-first knowledge graph AI.

    QUERY STRATEGY (choose the right tool for each question):

    1. CONCEPT LOOKUP → search_concepts()
       When: user asks about a topic/concept broadly
       Example: "What do we know about renewable energy?"

    2. ENTITY DEEP-DIVE → explore_entity()
       When: user asks about a specific entity by name
       Example: "Tell me about Tesla" / "What's connected to Node X?"

    3. RELATIONSHIP FINDING → find_path()
       When: user asks how two things relate
       Example: "How does Elon Musk connect to SpaceX?"

    4. COMPLEX ANALYTICS → query_graph() [Text2Cypher]
       When: user asks questions with filters, aggregations, conditions
       Example: "Which organizations have more than 5 people?"

    5. DEEP CONTEXT → deep_search()
       When: user needs rich understanding spanning multiple concepts
       Example: "Explain the landscape of AI regulation"

    6. BIG PICTURE → get_communities()
       When: user asks about themes, overview, main topics
       Example: "What are the main themes?" / "Give me an overview"

    ALWAYS narrate what you're doing and why:
    "I'm searching the graph for entities related to renewable energy...
     I found 12 relevant entities. Let me highlight them for you..."

    After EVERY query that returns graph data:
    - Call highlight_nodes() to visually show the results
    - Narrate the findings conversationally
    - Offer follow-up: "Would you like me to expand any of these nodes?"

    NEVER just return raw data — always explain and visualize.""",
    tools=[
        search_concepts, explore_entity, find_path,
        query_graph, deep_search, get_communities,
        get_ontology_info, get_graph_stats,
        highlight_nodes, expand_node, dim_nodes,
        add_node, add_relationship,
        ingest_document, google_search,
    ],
    sub_agents=[
        DataIngestionAgent,
        OntologyAgent,
        CSVAnalysisAgent,
        ExplanationAgent,
    ]
)
```

### Pre-built Cypher Templates (NOT Text2Cypher — for speed + reliability)

```python
CYPHER_TEMPLATES = {
    "explore_entity": """
        MATCH (n)-[r]-(m)
        WHERE n.name =~ '(?i).*{entity_name}.*'
        RETURN n, type(r) as rel_type, r, m
        LIMIT 50
    """,
    "find_path": """
        MATCH (a), (b)
        WHERE a.name =~ '(?i).*{entity_a}.*' AND b.name =~ '(?i).*{entity_b}.*'
        MATCH path = shortestPath((a)-[*1..{max_hops}]-(b))
        RETURN path
    """,
    "entity_types": """
        MATCH (n)
        RETURN DISTINCT labels(n) as types, count(n) as count
        ORDER BY count DESC
    """,
    "most_connected": """
        MATCH (n)-[r]-()
        RETURN n.name, labels(n), count(r) as connections
        ORDER BY connections DESC
        LIMIT 20
    """,
    "recent_additions": """
        MATCH (n)
        WHERE n.created_at IS NOT NULL
        RETURN n
        ORDER BY n.created_at DESC
        LIMIT 20
    """,
}
```

---

## Voice-Controlled Ontology Editing (OntologyAgent)

Users edit the ontology through natural voice commands. The agent manipulates an internal JSON representation, validates with rdflib, and persists as Turtle.

### Internal Ontology Format (Agent-Friendly JSON)

```json
{
  "metadata": {
    "name": "VoiceGraph Domain Ontology",
    "namespace": "http://voicegraph.ai/ontology/",
    "version": "1.2",
    "modified": "2026-03-28T10:00:00Z"
  },
  "classes": {
    "Person": {
      "uri": "http://voicegraph.ai/ontology/Person",
      "label": "Person",
      "subClassOf": "Thing",
      "description": "A human individual"
    },
    "Organization": {
      "uri": "http://voicegraph.ai/ontology/Organization",
      "label": "Organization",
      "subClassOf": "Thing",
      "description": "A company, institution, or group"
    }
  },
  "objectProperties": {
    "worksAt": {
      "uri": "http://voicegraph.ai/ontology/worksAt",
      "label": "works at",
      "domain": "Person",
      "range": "Organization",
      "description": "Employment relationship"
    }
  },
  "datatypeProperties": {
    "hasName": {
      "uri": "http://voicegraph.ai/ontology/hasName",
      "label": "has name",
      "domain": "Thing",
      "range": "xsd:string"
    }
  }
}
```

### OntologyAgent Definition

```python
ontology_agent = Agent(
    name="OntologyAgent",
    model="gemini-2.5-flash",
    description="Manages the knowledge graph ontology schema via voice commands",
    instruction="""You help users modify the knowledge graph ontology through voice.

    BEHAVIORS:
    - Always call get_ontology() first to see current state
    - Confirm destructive operations before executing
    - After adding new types, ask: "Should I re-scan documents for this new type?"
    - When adding a property, clarify domain and range if not specified
    - Explain changes in plain language

    EXAMPLE INTERACTIONS:
    User: "Add a new entity type called Project"
    You: add_class("Project", "Thing", "A planned undertaking")
         → "I've added Project as a new entity type under Thing."

    User: "Make Person related to Organization through 'works at'"
    You: add_object_property("worksAt", "Person", "Organization")
         → "Done. Persons can now have a 'works at' relationship to Organizations."

    User: "Remove the uses relationship"
    You: "Are you sure you want to remove 'uses'? This will also remove
          existing relationships of this type from the graph."
    """,
    tools=[
        get_ontology,              # Read current ontology JSON
        add_class,                 # Add OWL class
        remove_class,              # Remove class (with confirmation)
        rename_class,              # Rename class + update all refs
        add_object_property,       # Add relationship type
        remove_object_property,    # Remove relationship type
        add_datatype_property,     # Add attribute type
        remove_datatype_property,  # Remove attribute type
        set_subclass,              # Set class hierarchy
        list_classes,              # List all entity types
        list_properties,           # List all relationship/attribute types
        validate_ontology,         # Check consistency (rdflib)
        trigger_re_extraction,     # Re-extract with updated ontology
    ]
)
```

### Ontology Change Propagation

When the ontology changes, the system can selectively re-extract:

```python
async def trigger_re_extraction(scope: str = "new_types") -> dict:
    """Re-extract from source documents after ontology changes.

    scope options:
    - 'new_types': Only scan for newly added classes/properties (fast)
    - 'modified': Re-extract for changed types (medium)
    - 'full': Complete re-extraction with new ontology (slow, expensive)
    """
    if scope == "new_types":
        # Get newly added classes from ontology diff
        new_classes = get_ontology_diff().added_classes
        # Re-scan existing chunks for instances of new types only
        for chunk in get_all_chunks():
            extract_for_classes(chunk, new_classes, ontology_subset=new_classes)
    elif scope == "full":
        # Clear entity graph, keep Document/Chunk nodes, re-run Phase C
        clear_entity_graph()
        run_phase_c(current_ontology)
```

### Voice Command Examples

| Voice Command | Agent Action | Tool Called |
|---|---|---|
| "Add a new entity type called Project" | Creates OWL class | `add_class("Project", "Thing", "A planned undertaking")` |
| "Make Person related to Organization through 'works at'" | Creates object property | `add_object_property("worksAt", "Person", "Organization")` |
| "Remove the 'uses' relationship type" | Confirms, then removes | `remove_object_property("uses")` |
| "Make Employee a subclass of Person" | Sets hierarchy | `set_subclass("Employee", "Person")` |
| "What entity types do we have?" | Lists classes | `list_classes()` |
| "Show me all relationships" | Lists properties | `list_properties()` |
| "Is the ontology consistent?" | Validates | `validate_ontology()` |
| "Now re-scan documents for the new Project type" | Selective re-extraction | `trigger_re_extraction("new_types")` |
| "Rebuild the whole graph with the updated schema" | Full re-extraction | `trigger_re_extraction("full")` |

---

## Function Calling in Gemini Live Session

When user says: *"Show me how machine learning relates to neural networks"*

```
1. Gemini Live receives audio → understands intent
2. Agent selects find_path tool (relationship question)
3. Emits function call: find_path(
     entity_a="Machine Learning",
     entity_b="Neural Networks",
     max_hops=5
   )
4. Backend executes pre-built Cypher template → returns path
5. Agent calls: highlight_nodes(
     nodeIds=["ml_001", "dl_003", "nn_007"],
     edgeIds=["e_042", "e_089"]
   )
6. Backend pushes WebSocket event to frontend:
   { type: 'highlight', nodeIds: [...], edgeIds: [...] }
7. Frontend Reagraph animates: dims all nodes, highlights query result path
8. Gemini Live receives function results → narrates:
   "I can see that Machine Learning connects to Neural Networks
    through Deep Learning. Neural Networks are a subset of ML
    techniques. Would you like me to expand any of these nodes?"
9. Total round-trip: <1 second
```

When user says: *"Upload this PDF about climate research"*

```
1. Gemini Live receives audio → routes to DataIngestionAgent
2. Agent calls: ingest_document(file_path=..., type="pdf")
3. Backend runs 3-phase pipeline:
   Phase A → discovers entities (5-10 seconds)
   Phase B → generates/updates ontology (3-5 seconds)
   Phase C → precision extraction (5-10 seconds)
4. During extraction, WebSocket streams progress:
   { type: 'ingestion_status', status: 'processing',
     details: 'Discovered 34 entities in Phase A...' }
   { type: 'node_added', node: {...} }  // nodes appear one by one
5. Gemini narrates: "I'm processing the PDF... I've found 34 entities
   so far including 12 researchers, 8 organizations, and 14 concepts.
   Building the ontology now... Done! 47 entities and 89 relationships
   added to the graph. The main new concepts are..."
```

---

## "Thinking Through the Graph" — Dynamic Visualization System

This is our key differentiator. No existing tool does this. The graph is not a static display — it's a living, breathing visualization of the agent's reasoning process.

### Animation Modes (all three active simultaneously)

#### Mode 1: Sequential Path Glow (for relationship/path queries)

When the agent traverses a path (e.g., "How does X relate to Y?"), nodes light up sequentially along the traversal path like electricity flowing through wires.

```
User: "How does Machine Learning relate to Neural Networks?"

Timeline:
  t=0ms    All nodes dim to 20% opacity
  t=100ms  "Machine Learning" node pulses bright (agent found start)
           WebSocket: { type: 'thinking_step', step: 'found_start', nodeId: 'ml_001' }

  t=300ms  Edge ML→DL glows, "Deep Learning" lights up
           WebSocket: { type: 'thinking_traverse', fromId: 'ml_001', toId: 'dl_003',
                        edgeId: 'e_042' }

  t=500ms  Edge DL→NN glows, "Neural Networks" lights up
           WebSocket: { type: 'thinking_traverse', fromId: 'dl_003', toId: 'nn_007',
                        edgeId: 'e_089' }

  t=700ms  Full path pulses with a traveling particle effect
           WebSocket: { type: 'thinking_complete', path: ['ml_001','dl_003','nn_007'],
                        edges: ['e_042','e_089'] }

  Meanwhile: Gemini narrates each step in real-time as it happens
```

**Implementation:**
- Backend emits `thinking_step` events DURING tool execution, not just at the end
- Each step includes a 100-200ms stagger for visual drama
- Use Reagraph's `actives` prop for glow + custom CSS keyframe animations for pulse
- Traveling particle along edges using CSS `@keyframes` with `offset-path`

#### Mode 2: Ripple Expansion (for exploration/neighborhood queries)

When the agent explores an entity's neighborhood, a ripple expands outward from the center entity in concentric rings.

```
User: "Tell me about OpenAI"

Timeline:
  t=0ms    All nodes dim
  t=100ms  "OpenAI" center node pulses with a bright ring
           Ring 0 = just the entity itself

  t=400ms  Ring 1 expands: all direct neighbors light up simultaneously
           with a fade-in animation (opacity 0→1 over 200ms)
           Edges connecting ring 0→ring 1 glow

  t=800ms  Ring 2 expands: neighbors-of-neighbors light up
           with slightly dimmer glow (80% vs 100%)
           Edges connecting ring 1→ring 2 glow softer

  t=1200ms Agent narrates: "OpenAI connects to 5 people,
            3 products, and 2 research areas..."

  Rings beyond the query depth stay dim
```

**Implementation:**
- Backend computes rings (BFS from center node) and sends them as separate events
- Frontend uses `requestAnimationFrame` + staggered `setTimeout` for ring expansion
- Each ring has decreasing brightness: ring 0 = 100%, ring 1 = 80%, ring 2 = 60%
- Use CSS `box-shadow` or glow filter for the ring pulse effect

#### Mode 3: Thought Stream Overlay (always visible during agent reasoning)

A semi-transparent overlay panel shows the agent's reasoning steps in real-time, with visual connectors pointing to relevant nodes.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│        ○───○───●                                        │
│       / \     / \                                       │
│      ●    ○  ○   ○  ◄─────────────┐                    │
│       \  /  / \                    │                    │
│        ○───○   ○                   │                    │
│                                    │                    │
│   ┌────────────────────────────────┴──────────────┐     │
│   │  🧠 Searching for "renewable energy"...       │     │
│   │  👁 Found 12 related entities                  │     │
│   │  🔍 Exploring Solar Power (5 connections)      │←───│─── arrow points to Solar Power node
│   │  🔍 Exploring Wind Energy (3 connections)      │     │
│   │  ✅ Path found: Solar → Grid → Policy          │     │
│   │  ▌                                             │     │
│   └────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

**Implementation:**
- Floating panel at bottom of graph view, glass-morphism style (backdrop-filter: blur)
- Each line appears with a typewriter effect as the agent thinks
- Icons match TrustGraph's pattern: 🧠 Thinking, 👁 Observation, 🔍 Exploring, ✅ Found
- When a line mentions a specific node, a thin animated SVG line connects the text to the node
- Panel auto-hides 3 seconds after the agent finishes reasoning
- Panel is scrollable if reasoning is long

### WebSocket Events for Thinking Visualization

```typescript
// New thinking-specific server events
type ThinkingEvent =
  | { type: 'thinking_start'; query: string }                    // agent begins reasoning
  | { type: 'thinking_step'; step: string; icon: '🧠'|'👁'|'🔍'|'✅';
      nodeId?: string }                                           // reasoning step text
  | { type: 'thinking_traverse'; fromId: string; toId: string;
      edgeId: string; delay_ms: number }                          // path traversal animation
  | { type: 'thinking_ripple'; centerId: string;
      rings: string[][] }                                          // ripple expansion data
  | { type: 'thinking_complete'; resultNodeIds: string[];
      resultEdgeIds: string[] }                                    // final highlighted result
  | { type: 'thinking_clear' }                                    // reset all highlights
```

### How Backend Emits Thinking Events

The key is that each agent tool emits thinking events DURING execution, not just returning results at the end:

```python
async def find_path(entity_a: str, entity_b: str, max_hops: int = 5) -> dict:
    # Emit: thinking started
    await ws.send_event({ "type": "thinking_start", "query": f"Finding path: {entity_a} → {entity_b}" })

    # Step 1: Find start node
    start = await neo4j.find_entity(entity_a)
    await ws.send_event({ "type": "thinking_step", "step": f"Found {entity_a}",
                          "icon": "👁", "nodeId": start.id })
    await asyncio.sleep(0.15)  # dramatic pause for animation

    # Step 2: Find end node
    end = await neo4j.find_entity(entity_b)
    await ws.send_event({ "type": "thinking_step", "step": f"Found {entity_b}",
                          "icon": "👁", "nodeId": end.id })
    await asyncio.sleep(0.15)

    # Step 3: Find shortest path
    await ws.send_event({ "type": "thinking_step", "step": "Traversing graph...",
                          "icon": "🧠" })
    path = await neo4j.shortest_path(start.id, end.id, max_hops)

    # Step 4: Emit traversal events one-by-one for animation
    for i in range(len(path.nodes) - 1):
        await ws.send_event({
            "type": "thinking_traverse",
            "fromId": path.nodes[i].id,
            "toId": path.nodes[i+1].id,
            "edgeId": path.edges[i].id,
            "delay_ms": 150
        })
        await asyncio.sleep(0.15)

    # Step 5: Complete
    await ws.send_event({
        "type": "thinking_complete",
        "resultNodeIds": [n.id for n in path.nodes],
        "resultEdgeIds": [e.id for e in path.edges]
    })

    return {"path": path.to_dict(), "length": len(path.nodes)}
```

```python
async def explore_entity(entity_name: str, depth: int = 2) -> dict:
    # Emit: thinking started
    await ws.send_event({ "type": "thinking_start", "query": f"Exploring: {entity_name}" })

    # Find center
    center = await neo4j.find_entity(entity_name)
    await ws.send_event({ "type": "thinking_step", "step": f"Found {entity_name}",
                          "icon": "👁", "nodeId": center.id })

    # BFS to get rings
    rings = await neo4j.bfs_rings(center.id, depth)
    # rings = [["center"], ["neighbor1", "neighbor2"], ["n_of_n_1", ...]]

    await ws.send_event({
        "type": "thinking_ripple",
        "centerId": center.id,
        "rings": rings
    })

    # Narrate what was found
    await ws.send_event({ "type": "thinking_step",
        "step": f"Found {sum(len(r) for r in rings)} connected entities across {len(rings)} levels",
        "icon": "✅" })

    return {"center": center.to_dict(), "rings": rings, "total": sum(len(r) for r in rings)}
```

### Frontend Animation Implementation (React)

```typescript
// hooks/useThinkingAnimation.ts — core animation logic

function useThinkingAnimation(graphRef: RefObject<GraphCanvasRef>) {
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
  const [activeNodes, setActiveNodes] = useState<Set<string>>(new Set());
  const [activeEdges, setActiveEdges] = useState<Set<string>>(new Set());
  const [dimAll, setDimAll] = useState(false);

  const handleThinkingEvent = useCallback((event: ThinkingEvent) => {
    switch (event.type) {
      case 'thinking_start':
        setDimAll(true);         // dim entire graph
        setActiveNodes(new Set());
        setActiveEdges(new Set());
        setThinkingSteps([]);
        break;

      case 'thinking_step':
        // Add step to thought stream with typewriter effect
        setThinkingSteps(prev => [...prev, {
          text: event.step,
          icon: event.icon,
          nodeId: event.nodeId,
          timestamp: Date.now()
        }]);
        // Highlight referenced node
        if (event.nodeId) {
          setActiveNodes(prev => new Set(prev).add(event.nodeId));
        }
        break;

      case 'thinking_traverse':
        // Sequential path glow — add with stagger
        setTimeout(() => {
          setActiveNodes(prev => new Set(prev).add(event.toId));
          setActiveEdges(prev => new Set(prev).add(event.edgeId));
        }, event.delay_ms);
        break;

      case 'thinking_ripple':
        // Ripple expansion — each ring with increasing delay
        event.rings.forEach((ring, ringIndex) => {
          setTimeout(() => {
            setActiveNodes(prev => {
              const next = new Set(prev);
              ring.forEach(id => next.add(id));
              return next;
            });
          }, ringIndex * 400);  // 400ms between rings
        });
        break;

      case 'thinking_complete':
        // Final state — all result nodes/edges glowing
        setActiveNodes(new Set(event.resultNodeIds));
        setActiveEdges(new Set(event.resultEdgeIds));
        break;

      case 'thinking_clear':
        setDimAll(false);
        setActiveNodes(new Set());
        setActiveEdges(new Set());
        setThinkingSteps([]);
        break;
    }
  }, []);

  return { thinkingSteps, activeNodes, activeEdges, dimAll, handleThinkingEvent };
}
```

---

## Frontend Components

### 1. Graph View (Main)
- **Reagraph** 3D force-directed graph
- Full graph visible, color-coded by entity type (from ontology classes)
- **Thinking animation layer** (see above):
  - Sequential path glow during traversals
  - Ripple expansion during explorations
  - All non-active nodes dim to 20% opacity during thinking
  - Active nodes have pulsing glow animation (CSS `@keyframes pulse`)
  - Active edges have traveling particle effect
- Click node → side panel with entity details, provenance, source document
- Right-click → context menu (expand, collapse, hide, pin)
- Edge labels visible on hover
- Minimap in corner

### 2. Thought Stream Panel (always visible during reasoning)
- Floating glass-morphism panel at bottom-right of graph view
- Shows agent reasoning steps in real-time with icons (🧠 👁 🔍 ✅)
- Each line appears with typewriter animation
- SVG connector lines from text mentions to actual graph nodes
- Auto-hides 3s after reasoning completes
- Scrollable for long reasoning chains

### 3. Voice Panel
- Always-on microphone indicator with pulse animation
- Audio waveform visualization (real-time, using Web Audio API)
- Transcript overlay (what user said / what Gemini said)
- Connection status indicator (WebSocket health)
- Compact mode: just mic icon + waveform when not actively speaking

### 4. Ingestion Panel
- Drag-and-drop zone for files (PDF, audio, video, CSV, text)
- URL/YouTube link input field
- Upload progress with phase indicators:
  - Phase A: "Discovering entities..." + nodes appearing with fade-in
  - Phase B: "Generating ontology..." + ontology tree building
  - Phase C: "Precision extraction..." + nodes flying in with trails
  - "Done: 47 entities, 89 relationships"
- New nodes animate in from the edge of the graph during extraction

### 5. Info Sidebar
- Selected node: name, type, description, all properties
- Connected relationships with edge labels and target names
- Provenance: source document name, chunk text excerpt, confidence score
- "Ask about this" button → sends voice query about selected node

### 6. Ontology View (toggleable panel)
- Visual tree of current OWL class hierarchy
- List of relationship types with domain → range
- Live updates when OntologyAgent makes changes via voice
- Badge counts: how many entities per class
- Animates when ontology changes (new class slides in, removed class fades out)

### 7. Canvas (V1.1 Stretch)
- Triggered by voice: "Open canvas and explain X"
- Full-screen React rendering space
- Agent generates React components on-the-fly
- Flowcharts, comparison tables, timelines, image grids
- User can voice-edit: "Make that box bigger", "Add another step"

---

## API Endpoints

### REST API
```
POST   /api/ingest              # Upload file/URL for ingestion
POST   /api/ingest/csv          # Upload CSV for auto-analysis
GET    /api/graph               # Full graph data (nodes + edges)
GET    /api/graph/node/:id      # Node details + neighborhood
POST   /api/graph/query         # Execute Cypher query
GET    /api/ontology            # Get current ontology (JSON)
PUT    /api/ontology            # Update ontology
GET    /api/ontology/turtle     # Get ontology as Turtle
GET    /api/stats               # Graph statistics
GET    /api/communities         # Community summaries
POST   /api/search              # Semantic search
```

### WebSocket
```
WS     /ws/voice                # Gemini Live audio bidirectional stream
                                # Events:
                                #   client → server: audio_chunk, text_input
                                #   server → client: audio_chunk, transcript,
                                #                    graph_update, highlight,
                                #                    node_added, edge_added,
                                #                    ingestion_status,
                                #                    ontology_changed,
                                #                    agent_thinking
```

### WebSocket Event Protocol

```typescript
// Client → Server
type ClientEvent =
  | { type: 'audio_chunk'; data: string }           // base64 PCM 16-bit 16kHz
  | { type: 'text_input'; text: string }             // text fallback
  | { type: 'ingest_file'; file: string; name: string; mimeType: string }
  | { type: 'ingest_url'; url: string }
  | { type: 'graph_action'; action: 'expand' | 'collapse' | 'pin'; nodeId: string }

// Server → Client
type ServerEvent =
  // Audio
  | { type: 'audio_chunk'; data: string }            // base64 PCM 24kHz response
  | { type: 'transcript'; role: 'user' | 'agent'; text: string }
  // Graph mutations
  | { type: 'graph_update'; nodes: Node[]; edges: Edge[] }
  | { type: 'node_added'; node: Node }
  | { type: 'edge_added'; edge: Edge }
  | { type: 'node_removed'; nodeId: string }
  // Thinking animations (THE DIFFERENTIATOR)
  | { type: 'thinking_start'; query: string }
  | { type: 'thinking_step'; step: string; icon: '🧠'|'👁'|'🔍'|'✅'; nodeId?: string }
  | { type: 'thinking_traverse'; fromId: string; toId: string; edgeId: string; delay_ms: number }
  | { type: 'thinking_ripple'; centerId: string; rings: string[][] }
  | { type: 'thinking_complete'; resultNodeIds: string[]; resultEdgeIds: string[] }
  | { type: 'thinking_clear' }
  // Status
  | { type: 'ingestion_status'; phase: 'A'|'B'|'C'|'done'; details: string; progress: number }
  | { type: 'ontology_changed'; change: OntologyChange }
  | { type: 'csv_analysis'; result: CSVAnalysisResult }
  | { type: 'error'; message: string }
```

---

## Execution Plan — Parallel Workstreams

### Person A (You) — Backend + Agents + Voice + Pipeline
### Person B (Teammate) — Frontend + Graph Viz + UI + Audio

---

### Phase 1: Foundation (Days 1-3)

| Task | Owner | Depends On | Est. Hours |
|---|---|---|---|
| **1.1** Set up monorepo (pnpm workspaces) | A | — | 1h |
| **1.2** Init React + Vite + TypeScript + Tailwind + shadcn/ui | B | — | 2h |
| **1.3** Init Python FastAPI backend with WebSocket | A | — | 2h |
| **1.4** Set up Neo4j AuraDB Free + install `neo4j-graphrag[google]` | A | — | 1h |
| **1.5** Basic Reagraph component rendering static test data | B | 1.2 | 3h |
| **1.6** ADK hello-world agent with one function tool | A | 1.3 | 2h |
| **1.7** WebSocket connection between frontend ↔ backend | A+B | 1.2, 1.3 | 2h |
| **1.8** Basic lint + type-check + build pipeline | A | 1.1 | 1h |

**Milestone:** Static graph renders, WebSocket connected, ADK agent responds to text

---

### Phase 2: Extraction Pipeline + Graph UI (Days 4-7)

| Task | Owner | Depends On | Est. Hours |
|---|---|---|---|
| **2.1** Multimodal pre-processing module (PDF via neo4j-graphrag PdfLoader, YouTube via youtube_transcript_api, URL via BeautifulSoup, audio/video via Gemini multimodal API) | A | 1.4 | 6h |
| **2.2** Phase A: Schema-free discovery pipeline using `SimpleKGPipeline(schema="FREE")` + `SchemaFromExistingGraphExtractor` | A | 2.1 | 4h |
| **2.3** Phase B: Ontology generation — Gemini prompt → OWL Turtle → rdflib parse → convert to GraphSchema | A | 2.2 | 5h |
| **2.4** Phase C: Precision extraction with ontology subsetting (TrustGraph pattern) + constrained `SimpleKGPipeline` | A | 2.3 | 6h |
| **2.5** Entity resolution (exact + fuzzy via neo4j-graphrag) + provenance tracking | A | 2.4 | 3h |
| **2.6** Graph data REST API (full graph, node details, Cypher query endpoint) | A | 2.5 | 2h |
| **2.7** Reagraph real-time updates via WebSocket (nodes/edges added dynamically) | B | 1.5, 1.7 | 4h |
| **2.8** Node click → info sidebar (details, provenance, relationships) | B | 1.5 | 3h |
| **2.9** Color coding by entity type + legend panel | B | 1.5 | 2h |
| **2.10** File upload drag-and-drop UI + URL input + phase progress indicators | B | 1.7 | 4h |
| **2.11** Graph animation: new nodes fly in during extraction | B | 2.7 | 3h |

**Milestone:** Upload a PDF → watch 3-phase extraction build the graph in real-time with ontology-guided precision

---

### Phase 3: Voice + Agentic Querying + Thinking UI (Days 8-11)

| Task | Owner | Depends On | Est. Hours |
|---|---|---|---|
| **3.1** Gemini Live WebSocket integration in backend (audio bidirectional stream) | A | 1.6 | 5h |
| **3.2** Agentic GraphRAG tools: search_concepts, explore_entity, find_path, query_graph (Text2Cypher), deep_search — with `thinking_*` WebSocket events emitted during execution | A | 2.6 | 7h |
| **3.3** Audio capture from browser microphone + streaming to backend | B | — | 3h |
| **3.4** Audio playback (Gemini voice responses via Web Audio API) | B | 3.3 | 2h |
| **3.5** `useThinkingAnimation` hook: handle thinking_start/step/traverse/ripple/complete events, manage activeNodes/activeEdges/dimAll state | B | 2.7 | 5h |
| **3.6** Sequential path glow animation: nodes light up one-by-one along traversal path with pulsing glow + traveling particle on edges | B | 3.5 | 4h |
| **3.7** Ripple expansion animation: concentric rings of nodes fading in with staggered timing | B | 3.5 | 3h |
| **3.8** Thought stream overlay panel: glass-morphism floating panel, typewriter text, icon badges (🧠👁🔍✅), SVG connectors to nodes | B | 3.5 | 4h |
| **3.9** ADK Orchestrator with all graph query tools + function calling in Live session | A | 3.1, 3.2 | 5h |
| **3.10** Voice panel UI (waveform viz, transcript, status) | B | 3.3, 3.4 | 3h |
| **3.11** End-to-end: voice query → thinking animation → graph highlight → voice narration | A+B | 3.9, 3.6, 3.7, 3.8 | 4h |

**Milestone:** Talk to the graph, see nodes light up as the agent thinks through its reasoning, hear narrated explanations

---

### Phase 4: Advanced Features + Polish (Days 11-13)

| Task | Owner | Depends On | Est. Hours |
|---|---|---|---|
| **4.1** OntologyAgent: voice-controlled ontology editing (add/remove/rename classes, properties) | A | 2.3, 3.5 | 5h |
| **4.2** CSVAnalysisAgent: auto-detect schema + import CSV as graph/relational/document | A | 2.6 | 5h |
| **4.3** Ontology change propagation (selective re-extraction) | A | 4.1 | 3h |
| **4.4** Audio/video file ingestion via Gemini multimodal API | A | 2.1 | 3h |
| **4.5** Camera/screen vision: Gemini Live sees the graph UI state (capture canvas → send frames) | A | 3.1 | 4h |
| **4.6** Ontology view panel (class hierarchy tree, relationship types, live updates) | B | 2.7 | 3h |
| **4.7** Node expand/collapse animations + context menu (right-click) | B | 2.7 | 3h |
| **4.8** Dark theme + final UI polish + loading states + error states | B | — | 4h |
| **4.9** Community detection + summaries (get_communities tool) | A | 3.2 | 3h |
| **4.10** Deploy to Cloud Run via `adk deploy cloud_run` | A | all | 3h |

**Milestone:** Polished, deployed, full-featured demo-ready application

---

### Phase 5: Demo Prep (Day 14)

| Task | Owner | Depends On | Est. Hours |
|---|---|---|---|
| **5.1** Curate demo dataset: 3-4 PDFs + YouTube link + CSV + audio file (pick a compelling domain) | A | — | 2h |
| **5.2** Pre-build ontology for demo domain (hand-tuned for quality) | A | — | 1h |
| **5.3** Architecture diagram for presentation | B | — | 1h |
| **5.4** Demo script: 5-8 minute narrative hitting all judge criteria | A+B | — | 2h |
| **5.5** Stress test: latency, edge cases, error recovery | A | — | 2h |
| **5.6** Record backup demo video | A+B | — | 1h |

---

## Demo Strategy

**Story Arc for 5-8 minute presentation:**

1. **Hook (30s):** "What if you could talk to your data and literally see it think?"
2. **Upload multimodal (1.5min):** Drop 3 PDFs + YouTube link + CSV file → watch 3-phase extraction build the graph live. "Right now it's discovering entities... now generating an ontology... now doing precision extraction."
3. **Voice explore (2min):** Natural voice conversation exploring the graph:
   - "How does X relate to Y?" → path highlights + narration
   - "What are the main themes?" → community summaries
   - "Tell me more about this node" → entity deep-dive
4. **Voice edit ontology (1min):** "Add a new entity type called Regulation" → ontology updates → "Now re-scan the documents" → new nodes appear
5. **CSV magic (30s):** Upload a CSV → agent auto-detects it should be a graph → imports into Neo4j → new entities appear
6. **Vision (30s):** Point camera at screen → Gemini describes the graph state
7. **Architecture (1min):** Clean diagram: Gemini Live → ADK Agents → neo4j-graphrag → Neo4j → Reagraph
8. **Impact (30s):** "This isn't a chatbot. It's a thinking, visual, conversational knowledge system that understands the structure of your data."

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Gemini Live latency >2s under load | High — breaks "real person" feel | Pre-warm session, minimize function call payloads, use Flash model, pre-built Cypher templates |
| Neo4j AuraDB free tier pauses on inactivity | Medium — demo fails if DB sleeps | Keep-alive ping every 5 min, warm-up script before demo |
| $25 credit exhaustion | High — can't deploy | Monitor costs daily, use Gemini Flash (cheapest), cache embeddings, limit re-extraction |
| 3-phase extraction too slow for live demo | Medium — audience gets bored | Pre-extract most data, live-extract only 1 small document during demo |
| Ontology extraction quality poor | Medium — graph looks dumb | Hand-tune ontology for demo domain, curate demo data |
| 15-min Gemini Live session limit | Medium — demo might expire | Session rotation logic, keep demo under 10 min |
| Text2Cypher generates invalid Cypher | Medium — query fails | Fallback to pre-built templates, validate Cypher before execution |
| Reagraph performance with 500+ nodes | Low — graph laggy | Limit visible nodes, progressive disclosure, cluster small nodes |
| Cloud Run cold starts | Medium — first request slow | Min instances = 1 (~$3), pre-warm before demo |
| Entity resolution merges wrong entities | Low — graph inaccurate | Use conservative fuzzy threshold (0.85), review before demo |

---

## Cost Budget ($25 GCP Credits)

| Service | Estimated Cost | Notes |
|---|---|---|
| Cloud Run (backend) | ~$5-8 | With min 1 instance for demo |
| Gemini API (extraction — 3 phases) | ~$4-6 | Flash pricing, 3 passes over data |
| Gemini Live API (voice) | ~$3-5 | ~$0.023/min conversation |
| Gemini API (CSV analysis, Text2Cypher) | ~$1-2 | Occasional calls |
| Cloud Storage | ~$0.50 | Source files |
| Neo4j AuraDB | $0 | Free tier |
| Artifact Registry | ~$1 | Docker images |
| **Total estimated** | **~$15-23** | **Within budget (tight)** |

---

## Folder Structure

```
voicegraph/
├── frontend/                        # React app
│   ├── src/
│   │   ├── components/
│   │   │   ├── Graph/               # Reagraph wrapper + highlighting + animations
│   │   │   ├── VoicePanel/          # Mic, waveform, transcript, thinking indicator
│   │   │   ├── InfoSidebar/         # Node details, provenance, relationships
│   │   │   ├── IngestionPanel/      # File upload, URL input, phase progress
│   │   │   ├── OntologyView/        # Class hierarchy tree, relationship types
│   │   │   └── Canvas/              # V1.1 stretch
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts      # WS connection + event handling
│   │   │   ├── useVoice.ts          # Audio capture + playback
│   │   │   ├── useGraph.ts          # Graph state + highlighting logic
│   │   │   └── useThinkingAnimation.ts # Thinking UI: path glow, ripple, thought stream
│   │   ├── stores/                  # Zustand state
│   │   │   ├── graphStore.ts        # Nodes, edges, highlights
│   │   │   ├── voiceStore.ts        # Audio state, transcript
│   │   │   └── ontologyStore.ts     # Current ontology state
│   │   ├── types/                   # Shared TypeScript types
│   │   │   └── events.ts           # WebSocket event types
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── backend/                         # Python FastAPI
│   ├── agents/
│   │   ├── orchestrator.py          # ADK root agent (Gemini Live + all tools)
│   │   ├── graph_query.py           # GraphQueryAgent (agentic GraphRAG)
│   │   ├── ingestion.py             # DataIngestionAgent
│   │   ├── ontology_agent.py        # OntologyAgent (voice ontology editing)
│   │   ├── csv_agent.py             # CSVAnalysisAgent (auto schema detection)
│   │   └── tools/
│   │       ├── query_tools.py       # search_concepts, explore_entity, find_path,
│   │       │                        # query_graph, deep_search, get_communities
│   │       ├── graph_tools.py       # highlight_nodes, expand_node, dim_nodes,
│   │       │                        # add_node, add_relationship, get_graph_stats
│   │       ├── ontology_tools.py    # add_class, remove_class, rename_class,
│   │       │                        # add/remove properties, validate, re-extract
│   │       ├── ingest_tools.py      # ingest_document, parse multimodal
│   │       └── csv_tools.py         # profile_csv, heuristic_classify,
│   │                                # generate_schema, execute_import
│   ├── extraction/
│   │   ├── pipeline.py              # 3-phase orchestrator (A→B→C)
│   │   ├── phase_a.py               # Schema-free discovery (SimpleKGPipeline FREE)
│   │   ├── phase_b.py               # Ontology generation (Gemini → OWL → GraphSchema)
│   │   ├── phase_c.py               # Precision extraction (ontology-constrained)
│   │   ├── ontology_subsetter.py    # TrustGraph-inspired: embed OWL classes,
│   │   │                            # find relevant subset per chunk via vector similarity
│   │   ├── parsers/
│   │   │   ├── pdf_parser.py        # neo4j-graphrag PdfLoader
│   │   │   ├── youtube_parser.py    # youtube_transcript_api (from llm-graph-builder)
│   │   │   ├── url_parser.py        # BeautifulSoup / WebBaseLoader
│   │   │   ├── audio_parser.py      # Gemini multimodal API (native audio)
│   │   │   ├── video_parser.py      # Gemini multimodal API (frames + audio)
│   │   │   └── csv_parser.py        # pandas + ydata-profiling + Gemini analysis
│   │   └── ontology_manager.py      # OWL read/write via rdflib, JSON ↔ Turtle conversion,
│   │                                # validation, ontology diffing
│   ├── graph/
│   │   ├── neo4j_client.py          # Neo4j AuraDB connection + Cypher execution
│   │   ├── cypher_templates.py      # Pre-built Cypher templates for common queries
│   │   └── retrievers.py            # neo4j-graphrag retriever setup
│   │                                # (VectorRetriever, VectorCypherRetriever,
│   │                                #  Text2CypherRetriever, HybridRetriever)
│   ├── voice/
│   │   ├── gemini_live.py           # Gemini Live WebSocket handler
│   │   └── session.py               # Session management + rotation
│   ├── api/
│   │   ├── routes.py                # REST endpoints
│   │   └── websocket.py             # WS endpoint handlers
│   ├── main.py                      # FastAPI app entry
│   ├── requirements.txt
│   └── Dockerfile
├── shared/
│   └── events.json                  # WebSocket event schema (source of truth)
├── SESSION_LOG.md                   # Multi-session work log
├── CLAUDE.md                        # Claude agent instructions
├── PRD.md                           # This document
├── docker-compose.yaml              # Local dev
└── README.md                        # Team members, setup, architecture
```

---

## Key Dependencies

### Backend (requirements.txt)
```
# Core
fastapi>=0.110
uvicorn[standard]
websockets
python-dotenv

# Google / AI
google-adk
google-genai
google-cloud-aiplatform

# Neo4j + GraphRAG
neo4j
neo4j-graphrag[google,experimental,fuzzy-matching]

# Ontology
rdflib>=7.0

# Document parsing
youtube-transcript-api
beautifulsoup4
requests

# CSV analysis
pandas
ydata-profiling

# Utilities
pydantic>=2.0
```

### Frontend (package.json key deps)
```json
{
  "reagraph": "latest",
  "zustand": "latest",
  "tailwindcss": "latest",
  "@shadcn/ui": "latest"
}
```

---

## What We're NOT Building (Scope Cuts)

- No user authentication (demo only)
- No multi-user collaboration
- No persistent chat history across sessions
- No mobile responsive design
- No automated testing beyond smoke tests
- No CANVAS in MVP (V1.1 stretch)
- No full reasoner validation (rdflib lightweight checks only, no HermiT/Java)
- No cross-CSV foreign key detection (single CSV analysis only for MVP)
