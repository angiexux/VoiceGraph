# Knowledge Graph Repos -- Component Reuse Map

Date: 2026-03-28
Target stack: Gemini (via VertexAI) + Neo4j AuraDB + FastAPI

---

## 1. Neo4j LLM Graph Builder (MIT License)

**Repo:** `github.com/neo4j-labs/llm-graph-builder`
**All backend code lives in:** `backend/src/`

### 1.1 Document Loaders

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `document_sources/youtube.py` | 169 | Uses `youtube_transcript_api` to fetch transcripts, splits by configurable seconds (default chunk size), computes timestamps via `SequenceMatcher` fuzzy alignment. Returns `langchain Document` objects. | **Easy** -- standalone, only depends on `youtube_transcript_api` and langchain `Document`. Can strip langchain dependency trivially. |
| `document_sources/web_pages.py` | 21 | One-liner wrapper around `langchain_community.document_loaders.WebBaseLoader`. Calls `.load()` with `verify_ssl=False`. | **Trivial** -- replace with `httpx` + `BeautifulSoup` or `trafilatura` for better extraction. |
| `document_sources/wikipedia.py` | ~30 | Wikipedia loader via langchain. | **Trivial** |
| `document_sources/local_file.py` | ~50 | Handles local PDF upload. | **Easy** |
| `document_sources/gcs_bucket.py` | ~80 | GCS bucket integration for file storage. | **Medium** -- GCS-specific but pattern is reusable. |
| `document_sources/s3_bucket.py` | ~60 | S3 bucket integration. | **Medium** |

### 1.2 Chunking

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `create_chunks.py` | 78 | `CreateChunksofDocument` class. Uses `langchain_text_splitters.TokenTextSplitter`. Detects doc type by metadata keys (`page` = PDF, `length` = YouTube). Limits chunks for non-Neo4j users. | **Easy** -- the `TokenTextSplitter` call is the core; rest is routing logic. Replace with any token-based splitter. |

### 1.3 LLM Extraction (Graph Building)

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `llm.py` | 308 | `get_llm()` factory creates LangChain chat models from env vars (supports Gemini/OpenAI/Azure/Anthropic/Groq/Bedrock/Ollama/Diffbot). `get_graph_from_llm()` orchestrates extraction: combines chunks, creates `LLMGraphTransformer` (from `langchain_experimental`), calls `aconvert_to_graph_documents()`. Supports allowed nodes/relationships schema constraints and additional instructions. | **Medium** -- heavily coupled to LangChain's `LLMGraphTransformer`. The `LLMGraphTransformer` itself does the heavy lifting (structured output with tool calling). The factory pattern for models is useful but env-var-heavy. |
| `shared/schema_extraction.py` | ~50 | Schema extraction utilities. | **Easy** |

**Key insight:** The actual extraction prompt and JSON parsing is inside `langchain_experimental.graph_transformers.LLMGraphTransformer` -- not in this repo. This repo is an orchestrator around it.

### 1.4 Graph Writing / Neo4j Data Access

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `graphDB_dataAccess.py` | 608 | `graphDBdataAccess` class. CRUD for Document nodes, chunk management, KNN graph updates, duplicate detection (cosine + text distance via `apoc.text.distance`), duplicate merging via `apoc.refactor.mergeNodes`, vector index management. | **Medium** -- lots of useful Cypher queries for graph management. The duplicate detection query (lines 413-458) is particularly valuable. Uses `langchain_neo4j.Neo4jGraph` wrapper. For AuraDB, need to verify APOC availability. |
| `graph_query.py` | ~50 | Neo4j driver creation helper. | **Easy** |

### 1.5 Post-Processing

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `post_processing.py` | 187 | Three functions: (1) `create_vector_fulltext_indexes` -- creates vector + fulltext indexes on entities/chunks/communities. (2) `create_entity_embedding` -- embeds entity nodes (id + description). (3) `graph_schema_consolidation` -- uses an LLM to merge duplicate/similar node labels and relationship types via a cleanup prompt. | **High value, Medium difficulty** -- the schema consolidation approach (LLM-based label deduplication, lines 151-187) is a clever post-processing step. Index creation queries are directly reusable. |

### 1.6 Community Detection

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `communities.py` | 534 | Full GraphRAG-style community detection pipeline: GDS graph projection, Leiden algorithm, hierarchical community levels (up to 3), LLM-generated community summaries (title + summary), community embeddings, vector/fulltext indexes for communities. Uses `graphdatascience` library. | **Hard for AuraDB** -- requires Neo4j GDS (Graph Data Science) plugin which is NOT available on AuraDB Free tier. Available on AuraDB Enterprise. The community summary prompt templates and the LLM summarization chain are reusable independently. |

### 1.7 Chat / Retrieval Modes

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `QA_integration.py` | 699 | Full RAG pipeline with multiple modes: (1) **Vector search** -- Neo4jVector similarity search with document filtering. (2) **Entity vector mode** -- search entity embeddings. (3) **Global vector+fulltext mode** -- community-based search. (4) **Graph mode** -- `GraphCypherQAChain` (text-to-Cypher). Also includes: contextual compression retriever, question transformation (multi-turn), chat history summarization (background thread), session management via `Neo4jChatMessageHistory`. | **Medium** -- heavily LangChain-coupled but the retrieval query patterns and mode-switching architecture are instructive. The `CHAT_MODE_CONFIG_MAP` in `shared/constants.py` defines all modes with their index names, retrieval queries, and settings. |
| `shared/constants.py` | ~400 | All prompt templates, chat mode configurations, retrieval queries. Contains `CHAT_SYSTEM_TEMPLATE`, `QUESTION_TRANSFORM_TEMPLATE`, `GRAPH_CLEANUP_PROMPT`, `CHAT_MODE_CONFIG_MAP`. | **High value** -- the retrieval Cypher queries for each mode are production-tested patterns. |

---

## 2. TrustGraph (Apache 2.0 License)

**Repo:** `github.com/trustgraph-ai/trustgraph`
**Architecture:** Microservices via Pulsar message queues. Code spread across `trustgraph-base/`, `trustgraph-flow/`, `trustgraph-cli/`.

### 2.1 Ontology-Guided Extraction (OntoRAG)

This is TrustGraph's most distinctive feature -- constraining LLM extraction to OWL ontology classes.

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py` | 902 | Main `Processor` class. Pipeline: (1) Load ontology from config, (2) Embed ontology classes/properties into vector store, (3) For each text chunk: split into sentences, embed sentences, find matching ontology elements via vector similarity, build ontology subset, construct constrained prompt, call LLM, parse response, convert to triples. Emits PROV-O provenance triples per extraction. | **Hard** -- deeply coupled to Pulsar messaging. But the algorithm (vector-match text to ontology, build subset, constrain prompt) is the valuable pattern to replicate. |
| `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_loader.py` | 246 | `OntologyLoader` + `Ontology` dataclass. Parses JSON ontology definitions into `OntologyClass` and `OntologyProperty` objects. Supports: `rdfs:label`, `rdfs:comment`, `rdfs:subClassOf`, `owl:equivalentClass`, `owl:disjointWith`, `owl:ObjectProperty`, `owl:DatatypeProperty`, domain/range, inverse, cardinality. Validates structure (circular inheritance, dangling references). | **Easy to extract** -- pure Python dataclasses, no external dependencies. Directly reusable. |
| `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_selector.py` | 355 | `OntologySelector` class. For each text segment, embeds it and searches vector store for matching ontology elements. Builds `OntologySubset` containing only relevant classes/properties. Resolves dependencies (parent classes, property domains/ranges, inverse properties). Auto-includes properties related to selected classes. | **Medium** -- the algorithm is the key value. Uses an in-memory vector store. Can be reimplemented with any embedding + similarity search. |
| `trustgraph-flow/trustgraph/extract/kg/ontology/text_processor.py` | 240 | `TextProcessor` class. Uses NLTK for sentence splitting (`punkt_tab`), noun/verb phrase extraction via POS tagging, key term extraction (bigrams, stopword removal). | **Easy** -- standalone NLTK-based processing. |
| `trustgraph-flow/trustgraph/extract/kg/ontology/simplified_parser.py` | 346 | Parses LLM extraction responses. Supports two formats: JSONL (flat list with type discriminators) and legacy (nested dict). Extracts `Entity`, `Relationship`, `Attribute` dataclasses. | **Easy** -- pure Python, no dependencies. Very clean extraction result parser. |
| `trustgraph-flow/trustgraph/extract/kg/ontology/triple_converter.py` | 228 | Converts parsed extraction results into RDF triples (IRI terms). | **Easy** -- reusable pattern for converting entities/relationships to graph triples. |
| `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_embedder.py` | ~150 | Embeds ontology class labels/comments into vector store for similarity matching. | **Medium** -- depends on TrustGraph embeddings client. |
| `trustgraph-flow/trustgraph/extract/kg/ontology/vector_store.py` | ~100 | In-memory vector store with cosine similarity search. | **Easy** -- can replace with FAISS or similar. |

**How the ontology constraining works (the key algorithm):**
1. Load OWL ontology (classes + properties with domains/ranges)
2. Embed all ontology class labels and property labels
3. For each text chunk: split into sentences, embed sentences
4. Vector-search to find top-K matching ontology classes/properties
5. Build an `OntologySubset` containing only relevant schema elements
6. Resolve dependencies (add parent classes, domain/range classes)
7. Format the subset as prompt context: "Extract ONLY these entity types: [PersonClass, OrganizationClass, ...] with these relationships: [worksFor(Person->Org), ...]]"
8. LLM extracts; parser validates against schema

### 2.2 ReAct Agent

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `trustgraph-flow/trustgraph/agent/react/agent_manager.py` | 390 | `AgentManager` class. Text-based ReAct parsing (Thought/Action/Args/Final Answer). Supports streaming via `StreamingReActParser`. Multi-step reasoning loop with tool invocation. | **Medium** -- the ReAct parsing logic is solid but the whole thing is wired to Pulsar. The `parse_react_response()` method (lines 17-171) is a clean, self-contained ReAct text parser worth extracting. |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | 318 | Tool definitions: `KnowledgeTool`, `RelationshipsTool`, `DocumentTool`. Each has name, description, argument schema. | **Medium** -- tool definitions need rewiring to your graph store. |

### 2.3 Prompt Templates

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `trustgraph-flow/trustgraph/template/prompt_manager.py` | 198 | `PromptManager` class. Loads prompt configs from JSON, uses `ibis` templating. Supports system template + named prompt templates with response type and JSON schema validation. | **Easy** -- lightweight template management pattern. |

Prompt templates are stored as configuration (not hard-coded), loaded via config service at runtime.

### 2.4 Provenance Tracking

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `trustgraph-base/trustgraph/provenance/triples.py` | 678 | Full PROV-O provenance model. Functions: `document_triples()`, `derived_entity_triples()`, `subgraph_provenance_triples()`, `question_triples()`, `grounding_triples()`, `exploration_triples()`, `focus_triples()`, `synthesis_triples()`. Tracks: document -> pages -> chunks -> extracted subgraphs, with activities (who/what/when extracted), agents (components + versions), and query-time provenance (question -> grounding -> exploration -> focus -> synthesis). | **High value, Medium difficulty** -- the PROV-O model is excellent for audit trails. Pure Python, builds RDF-style triples. Needs adaptation from their Triple schema to Neo4j property graph format. |
| `trustgraph-base/trustgraph/provenance/uris.py` | ~50 | URI generators for provenance entities. | **Easy** |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | ~80 | Namespace constants (PROV-O, Dublin Core, TrustGraph custom). | **Easy** |

### 2.5 GraphRAG Query Pipeline

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` | 931 | `GraphRag` class. Pipeline: (1) Decompose query into concepts via LLM, (2) Embed concepts, (3) Vector-search for matching graph entities, (4) Fetch neighborhood triples (configurable path length, subgraph size limits), (5) Score/filter edges via LLM relevance scoring, (6) Build context from selected edges, (7) Generate answer with full provenance. Includes LRU cache with TTL for label lookups. | **Hard** -- deeply wired to Pulsar clients. But the algorithm (concept decomposition -> entity lookup -> subgraph expansion -> LLM edge scoring -> answer generation) is the state-of-the-art GraphRAG pattern. |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` | 463 | Service wrapper for `GraphRag`. Handles streaming, explainability output, librarian integration. | **Hard** -- Pulsar-specific. |
| `trustgraph-flow/trustgraph/retrieval/document_rag/` | ~300 | Document-based RAG (chunk retrieval rather than graph traversal). | **Medium** |

### 2.6 PDF/Document Parsing

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `trustgraph-flow/trustgraph/decoding/pdf/pdf_decoder.py` | 398 | Uses `langchain_community.document_loaders.PyPDFLoader`. Decodes base64 PDF data, extracts pages, saves each page as child document in librarian service, emits PROV-O provenance triples for document->page derivation. | **Medium** -- the `PyPDFLoader` call is trivial; the provenance emission pattern is the valuable part. |
| `trustgraph-ocr/trustgraph/decoding/ocr/pdf_decoder.py` | ~200 | OCR-based PDF decoder (for scanned documents). | **Medium** |

---

## 3. neo4j-graphrag-python (Apache 2.0 License)

**Repo:** `github.com/neo4j/neo4j-graphrag-python`
**Main code:** `src/neo4j_graphrag/`
**This is the most directly reusable repo** -- it's a library (not an app), with clean component abstractions.

### 3.1 SimpleKGPipeline

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `experimental/pipeline/kg_builder.py` | 201 | `SimpleKGPipeline` class. Orchestrator that wires: file loader -> text splitter -> entity/relation extractor -> KG writer. Configured via `SimpleKGPipelineConfig`. Accepts `GraphSchema` (node types, relationship types, patterns, constraints), optional entity resolution. Supports PDF and Markdown input. | **Easy** -- this is the recommended way to build a KG pipeline. Directly usable with `VertexAILLM` for Gemini. |
| `experimental/pipeline/config/template_pipeline/simple_kg_builder.py` | ~200 | Config model for SimpleKGPipeline. Resolves components, builds pipeline graph. | **Easy** -- internal config, used by SimpleKGPipeline. |
| `experimental/pipeline/pipeline.py` | ~300 | Generic pipeline execution engine with async component orchestration. | **Easy** -- use via SimpleKGPipeline. |

### 3.2 Schema Components

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `experimental/components/schema.py` | 1403 | Core schema models: `PropertyType`, `NodeType`, `RelationshipType`, `Pattern`, `ConstraintType`, `GraphSchema`. Plus two schema extractors: **`SchemaFromTextExtractor`** -- sends sample text to LLM, asks it to identify entity/relationship types, returns `GraphSchema`. **`SchemaFromExistingGraphExtractor`** -- reads existing Neo4j graph labels/relationships/properties via Cypher, builds schema from what's already in the DB. Also: `GraphSchemaFromFileLoader` (load schema from JSON/YAML), `GraphSchemaFromNodeNameExtractor` (from just node names). Supports `schema="EXTRACTED"` mode in SimpleKGPipeline to auto-discover schema from DB. | **High value, Easy** -- the schema models and extractors are immediately usable. The `GraphSchema` model with Pydantic validation is production-quality. |

### 3.3 Entity Resolution

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `experimental/components/resolver.py` | 471 | Three resolvers: (1) **`SinglePropertyExactMatchResolver`** -- merges entities with same label + exact property match (default: "name"). Uses `apoc.refactor.mergeNodes`. (2) **`FuzzyMatchResolver`** -- uses `rapidfuzz.fuzz.WRatio` for fuzzy string matching. Normalized 0-1 scores, configurable threshold (default 0.8). (3) **`SpaCySemanticMatchResolver`** -- uses spaCy embeddings + cosine similarity. All share `BasePropertySimilarityResolver` base class that handles: pairwise comparison, set consolidation (overlapping merge groups), batch APOC merge queries. | **Medium** -- requires APOC plugin on Neo4j (available on AuraDB). The fuzzy and semantic matching logic (lines 215-310) is reusable regardless of Neo4j. |

### 3.4 Retriever Implementations

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `retrievers/vector.py` | 392 | **`VectorRetriever`** -- vector similarity search via Neo4j vector index. **`VectorCypherRetriever`** -- vector search + custom Cypher traversal. Both support: embedder-based or raw vector input, `top_k`, `effective_search_ratio`, metadata filters, custom result formatters. | **Easy** -- directly usable with Neo4j AuraDB. Key class for RAG. |
| `retrievers/hybrid.py` | 417 | **`HybridRetriever`** -- combines vector + fulltext search. **`HybridCypherRetriever`** -- hybrid search + custom Cypher. | **Easy** -- requires both vector and fulltext indexes. |
| `retrievers/text2cypher.py` | 231 | **`Text2CypherRetriever`** -- LLM generates Cypher from natural language query. Auto-fetches schema if not provided. Includes `extract_cypher()` helper that handles code block extraction and backtick quoting for multi-word labels. | **Easy** -- directly usable. Very clean implementation. |
| `retrievers/tools_retriever.py` | ~100 | Tool-based retriever for agent frameworks. | **Easy** |
| `retrievers/external/pinecone/` | ~150 | Pinecone vector store integration. | N/A |
| `retrievers/external/qdrant/` | ~150 | Qdrant vector store integration. | N/A |
| `retrievers/external/weaviate/` | ~150 | Weaviate vector store integration. | N/A |
| `retrievers/base.py` | ~150 | Base `Retriever` class with `_fetch_index_infos` and `search` method. | **Easy** |

### 3.5 LLM Integrations

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `llm/vertexai_llm.py` | 630 | **`VertexAILLM`** class. Implements both `LLMInterface` (v1, string-based) and `LLMInterfaceV2` (message-based with structured output). Supports: `invoke`/`ainvoke` (sync/async), `invoke_with_tools`/`ainvoke_with_tools`, structured output via `response_format` (Pydantic model -> JSON schema), rate limiting. Uses `vertexai.generative_models.GenerativeModel`. Default model: `gemini-1.5-flash-001`. | **Directly usable** -- this is exactly what you need for Gemini. `supports_structured_output = True` means it works with the `LLMEntityRelationExtractor` in structured output mode. |
| `llm/openai_llm.py` | ~300 | OpenAI LLM integration. | Easy |
| `llm/base.py` | ~150 | `LLMInterface` and `LLMInterfaceV2` abstract base classes. | Easy |
| `llm/rate_limit.py` | ~100 | Rate limiting decorators. | Easy |

### 3.6 Entity Relation Extractor

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `experimental/components/entity_relation_extractor.py` | 390 | **`LLMEntityRelationExtractor`** class. Two modes: (1) **V1 (default)** -- prompt-based JSON extraction with `json_repair` for malformed output. (2) **V2 (structured output)** -- uses `LLMInterfaceV2` with `response_format=Neo4jGraph` Pydantic model. Both: run concurrently across chunks (configurable `max_concurrency`), build lexical graph (Document->Chunk->Entity relationships), prefix entity IDs with chunk ID for uniqueness. Error handling: RAISE or IGNORE per chunk. | **High value, Easy** -- core extraction component. Use with `VertexAILLM(use_structured_output=True)` for best results with Gemini. |

### 3.7 Other Useful Components

| File | Lines | What it does | Reuse difficulty |
|------|-------|-------------|-----------------|
| `experimental/components/pdf_loader.py` | 33 | Thin wrapper around `fsspec` for PDF loading. | **Trivial** |
| `experimental/components/data_loader.py` | ~80 | `DataLoader` base + PDF/Markdown loaders. | **Easy** |
| `experimental/components/text_splitters/` | ~200 total | `FixedSizeSplitter`, `LangChainTextSplitterAdapter`, `LlamaIndexTextSplitterAdapter`. | **Easy** |
| `experimental/components/lexical_graph.py` | ~200 | Builds Document->Chunk->Entity graph structure with NEXT_CHUNK relationships. | **Easy** |
| `experimental/components/kg_writer.py` | ~200 | `Neo4jWriter` -- batch upserts nodes/relationships to Neo4j with proper Cypher. | **Easy** -- directly usable with AuraDB. |
| `experimental/components/graph_pruning.py` | ~150 | Prunes extracted graph against schema (removes nodes/rels not in schema). | **Easy** |
| `experimental/components/embedder.py` | ~80 | Embeds text chunks for vector storage. | **Easy** |
| `embeddings/vertexai.py` | ~80 | VertexAI embeddings (text-embedding models). | **Easy** -- directly usable. |
| `generation/graphrag.py` | ~150 | `GraphRAG` class for retrieval + generation with any retriever. | **Easy** |
| `generation/prompts.py` | ~300 | All prompt templates: `ERExtractionTemplate`, `Text2CypherTemplate`, `RagTemplate`, `SchemaExtractionTemplate`. | **High value** -- production-tested prompts. |

---

## Summary: Recommended Extraction Priority

### Tier 1 -- Use directly (minimal adaptation)

| Component | Source | Why |
|-----------|--------|-----|
| `VertexAILLM` | neo4j-graphrag-python | Drop-in Gemini integration with structured output |
| `SimpleKGPipeline` | neo4j-graphrag-python | Full extraction pipeline orchestrator |
| `LLMEntityRelationExtractor` | neo4j-graphrag-python | Core extraction with structured output support |
| `GraphSchema` + schema models | neo4j-graphrag-python | Production-quality schema definition |
| `VectorRetriever` / `VectorCypherRetriever` | neo4j-graphrag-python | Vector search over Neo4j |
| `Text2CypherRetriever` | neo4j-graphrag-python | Natural language to Cypher |
| `HybridRetriever` | neo4j-graphrag-python | Combined vector + fulltext search |
| `SinglePropertyExactMatchResolver` | neo4j-graphrag-python | Entity deduplication |
| All prompt templates | neo4j-graphrag-python | Extraction, Cypher gen, RAG prompts |
| `Neo4jWriter` (kg_writer) | neo4j-graphrag-python | Batch graph writing |

### Tier 2 -- Extract and adapt

| Component | Source | Why |
|-----------|--------|-----|
| Ontology loader + selector algorithm | TrustGraph | Unique ontology-constrained extraction; extract the algorithm, reimplement without Pulsar |
| YouTube transcript extraction | llm-graph-builder | Clean `youtube_transcript_api` usage with timestamp alignment |
| PROV-O provenance model | TrustGraph | Excellent audit trail; adapt from RDF triples to Neo4j property graph |
| Schema consolidation (LLM-based) | llm-graph-builder | Post-processing to merge similar labels |
| ReAct response parser | TrustGraph | Clean text-based ReAct format parser |
| Duplicate detection queries | llm-graph-builder | Cypher patterns for cosine + text distance matching |
| Fuzzy/semantic entity resolution | neo4j-graphrag-python | `FuzzyMatchResolver` + `SpaCySemanticMatchResolver` |
| `SchemaFromTextExtractor` | neo4j-graphrag-python | Auto-discover schema from sample text |
| `SchemaFromExistingGraphExtractor` | neo4j-graphrag-python | Auto-discover schema from existing Neo4j graph |
| Chat mode architecture | llm-graph-builder | Mode-switching retrieval (vector/entity/community/graph) |

### Tier 3 -- Study the pattern, reimplement

| Component | Source | Why |
|-----------|--------|-----|
| GraphRAG query pipeline | TrustGraph | Concept decomposition -> entity lookup -> subgraph expansion -> LLM edge scoring. Too coupled to Pulsar to extract directly. |
| Community detection + summarization | llm-graph-builder | Requires GDS plugin (not on AuraDB Free). Study the Leiden + LLM summary pattern for future use. |
| Streaming ReAct agent | TrustGraph | Streaming token-by-token ReAct parsing. Cool but complex. |

---

## AuraDB Compatibility Notes

- **APOC**: Available on AuraDB (needed for entity resolution `apoc.refactor.mergeNodes`)
- **GDS**: NOT available on AuraDB Free. Available on AuraDB Enterprise. Communities require GDS.
- **Vector indexes**: Fully supported on AuraDB
- **Fulltext indexes**: Fully supported on AuraDB
- **No `db.create.setNodeVectorProperty`**: Use standard Cypher `SET n.embedding = $vec` instead on newer versions
