# VoiceGraph — Claude Code Instructions

## Project
Voice-first interactive knowledge graph for NYC Build With AI Hackathon. Uses Gemini Live + ADK + Neo4j + Reagraph.

## Session Protocol
1. **Start every session** by reading `SESSION_LOG.md` to understand what was done before
2. **End every session** by appending a new entry to `SESSION_LOG.md` with what was done, decisions made, and open items
3. Read `PRD.md` for full architecture and execution plan

## Tech Stack
- **Frontend:** React 18 + TypeScript + Vite + Tailwind + shadcn/ui + Reagraph
- **Backend:** Python FastAPI + WebSocket + Google ADK
- **Graph DB:** Neo4j AuraDB Free (Cypher queries via neo4j Python driver)
- **KG Builder:** `neo4j-graphrag[google,experimental,fuzzy-matching]` — handles extraction pipeline
- **Ontology:** rdflib + custom JSON format, OWL in Turtle serialization
- **Voice:** Gemini Live (Multimodal Live API) via ADK `run_live()`
- **LLM:** Gemini 2.5 Flash via `VertexAILLM` for extraction + Live voice
- **Deploy:** Google Cloud Run via `adk deploy cloud_run`

## Key Architecture Patterns
- **3-phase extraction:** Phase A (schema-free discovery) → Phase B (ontology generation) → Phase C (precision extraction with ontology subsetting)
- **Agentic GraphRAG:** 8 specialized query tools, agent selects the right one per question. Pre-built Cypher templates for speed, Text2Cypher only for complex queries.
- **Thinking UI:** 3 animation modes — sequential path glow, ripple expansion, thought stream overlay. Backend emits `thinking_*` WebSocket events DURING tool execution.
- **Voice ontology editing:** OntologyAgent with 13 function tools, rdflib validation, selective re-extraction after changes.
- **CSV auto-detection:** 3-stage pipeline (heuristic → Gemini → auto-import as graph/relational/document).

## Open Source Code We Reuse
- `neo4j-graphrag-python` (Apache 2.0) — extraction pipeline, retrievers, entity resolution
- `trustgraph` (Apache 2.0) — ontology subsetting pattern, provenance approach
- `llm-graph-builder` (MIT) — YouTube parser, schema consolidation, multi-mode chat

## WebSocket Events
All frontend-backend communication via typed JSON events. See PRD.md "WebSocket Event Protocol" section. Key event types:
- `audio_chunk` — voice audio bidirectional
- `thinking_*` — graph animation events (start, step, traverse, ripple, complete, clear)
- `graph_update`, `node_added`, `edge_added` — graph mutations
- `ingestion_status` — extraction pipeline progress

## Don't
- Don't add user auth — this is a demo
- Don't add mobile responsiveness
- Don't use LangChain or LlamaIndex — pure neo4j-graphrag + Gemini + ADK
- Don't over-engineer — hackathon code, ship fast
- Don't build Canvas yet (V1.1 stretch)
- Don't use HermiT/Java reasoner — rdflib lightweight checks only
