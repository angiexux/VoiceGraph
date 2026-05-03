# VoiceGraph — Session Log

This file is the shared work log for the team. Every Claude Code session and manual work session should be logged here so everyone knows what was built, changed, or decided.

**How to use:** Add a new entry at the top (newest first) with the format below.

---

## Session 8 — 2026-05-02 — Ingest rendering, graph fetch, UI spacing, latency tweaks

**Who:** Claude Code  
**Duration:** ~1 session

### What was done:
- **File ingest → graph:** Fixed plain-text/Markdown uploads routing through `parse_text` with a temp **file path** (was treating the path string as document content). Clear errors for `folder`/`audio` until those parsers exist.
- **Neo4j `get_full_graph`:** Replaced single `OPTIONAL MATCH … LIMIT` (could truncate nodes/edges on larger graphs) with separate bounded queries for nodes and relationships.
- **REST ingest:** `POST /api/ingest` now forwards `options` as pipeline metadata; `POST /api/ingest/file` accepts `collection_name` (Form) and passes metadata.
- **Frontend graph load:** After ingestion, if `/api/graph/summary` returns no rows but `total_nodes > 0`, automatically falls back to `/api/graph` once.
- **Ingestion store:** Added `startedAt` for BottomSheet elapsed-time UI (was undefined).
- **Polling / perceived latency:** Job poll interval 2s → 1s; normalized job statuses (`started`, `extracting_*`) for the stepper; WebSocket ingestion events use the same mapping.
- **UI spacing:** Increased app grid padding/gap, bottom bar padding, TopBar horizontal padding, BottomSheet padding; slightly faster force-graph warmup/cooldown.

### Open items:
- Zip folder and audio ingestion remain stubs (explicit error messages).
- End-to-end verify with real Neo4j + PDF/TXT upload.

---

## Session 6 — 2026-03-28 — Real Extraction Pipeline, UI Overhaul, Git Setup

**Who:** Claude Code
**Duration:** ~30 minutes

### What was done:

#### Gemini Extraction — Fixed & Verified End-to-End
- [x] Fixed `_call_gemini()` — was creating `genai.Client()` without API key, causing silent failures
- [x] Relaxed Phase C type filtering — if ontology generation fails, accepts all Gemini-extracted types instead of dropping everything
- [x] Cleared garbage data from Neo4j (had 5 nodes with names like "window", "sendEvent" from corrupted JS globals)
- [x] Verified full pipeline: text → Gemini 2.5 Flash → 13 entities + 11 relationships → stored in Neo4j
- [x] Real entity types: Person, Theory, Organization, Year, City, Country, Award, etc.

#### Full UI Color Palette Overhaul
- [x] Background: `#0b1326` (navy blue) → `#09090b` (near-black) — graph edges/arrows now visible
- [x] Glass panels: opaque navy → `rgba(24,24,27,0.82)` with zinc borders — clear contrast against background
- [x] Text hierarchy: zinc scale (#fafafa primary, #a1a1aa secondary, #71717a muted)
- [x] Accent: #f59e0b (amber), secondary: #34d399 (emerald)
- [x] Added 6 new entity type colors: Field, Method, Model, Architecture, Theory, Date
- [x] Graph theme updated: near-black canvas, visible edge/arrow colors (zinc-400 at 25%)

#### Component Fixes (All Panels)
- [x] LeftPanel — proper padding, stat cards with bg containers, clean entity type list
- [x] IngestionPanel — segmented control style, proper textarea, amber button, status badges with colored backgrounds
- [x] VoicePanel — cleaner pill design, proper text hierarchy, amber mic button
- [x] InfoSidebar — property cards with backgrounds, relationship buttons with borders
- [x] ThoughtStream — consistent spacing, proper dividers
- [x] Removed vignette overlay and ambient glow from App.tsx (caused muddy look)

#### Billing Cleanup
- [x] User unlinked billing from 3 old GCP projects (authentic-scout, gcloud-hackathon-3xf, gen-lang-client)
- [ ] vibrant-resource-8b2bd — permission denied, may need project owner

### Key decisions:
1. Near-black (#09090b) instead of navy blue — graph visualization needs dark neutral background, not colored
2. Zinc color scale for text/borders — industry standard for dark UIs (matches Vercel, Linear, etc.)
3. Phase C extraction is forgiving — if ontology parsing fails, keeps all entities instead of filtering to empty set

### Verified working:
- Real Gemini extraction: 13 nodes + 11 edges from Einstein paragraph
- Neo4j connected and persisting data
- Frontend builds clean (0 TS errors)
- Backend health check: `{"status":"ok","neo4j_connected":true}`

### Open items:
- [ ] Verify UI visually with user
- [ ] Test voice conversation with Gemini Live
- [ ] Push to GitHub for team access
- [ ] Build Canvas (V1.1)
- [ ] Cloud Run deployment
- [ ] Wire ADK agent to real queries (currently mock thinking animation)
- [ ] Ontology view panel

---

## Session 4 — 2026-03-28 — Voice Integration, Ingestion Pipeline, Frontend Features

**Who:** Claude Code (autonomous build session)
**Duration:** ~30 minutes (4 parallel agents)

### What was built:

#### Voice Integration (Frontend)
- [x] `useAudioCapture.ts` — Mic capture hook: getUserMedia → ScriptProcessorNode → 16-bit PCM 16kHz → base64 → WebSocket
- [x] `useAudioPlayback.ts` — Audio playback hook: base64 PCM 24kHz → AudioBufferSourceNode with seamless chaining
- [x] `VoicePanel.tsx` rewritten — Real mic recording, live canvas waveform from AnalyserNode, pulsing ring animation, connection status dot
- [x] `useWebSocket.ts` updated — Routes audio_chunk events to playback callback

#### Voice Integration (Backend)
- [x] `voice/session.py` — VoiceSession class managing Gemini Live API (gemini-2.0-flash-live-001), bidirectional audio streaming, function calling mid-conversation
- [x] `voice/tool_declarations.py` — 6 Gemini FunctionDeclarations (search_concepts, explore_entity, find_path, get_graph_stats, highlight_nodes, add_node)
- [x] `voice/tool_executor.py` — Maps Gemini function calls to actual Python tool functions, executes and returns results
- [x] `main.py` WebSocket handler updated — start_voice/audio_chunk/stop_voice event handling, voice session lifecycle

#### Ingestion System (Backend)
- [x] `ingestion/job_manager.py` — In-memory job tracker with status progression (started → parsing → extracting_phase_a/b/c → storing → complete)
- [x] `ingestion/ingest.py` — Full async ingestion flow: parse → chunk → Phase A/B/C extraction → Neo4j storage → WebSocket broadcasts
- [x] `POST /api/ingest` endpoint — Accepts text/URL/YouTube/PDF, kicks off background task, returns job_id
- [x] `GET /api/ingest/{job_id}` endpoint — Returns job status with progress
- [x] `ingest_tools.py` rewritten — Real implementation replacing stub, calls run_ingestion via asyncio

#### Frontend Features
- [x] Node click handling — onNodeClick in GraphView → selectNode in graphStore
- [x] InfoSidebar redesigned — Shows node details (type badge, properties table, relationships) or graph stats
- [x] `ingestionStore.ts` — Zustand store for ingestion progress tracking
- [x] `IngestionPanel.tsx` — Text/URL/YouTube input, PDF upload, live progress display
- [x] `LeftPanel.tsx` — Left sidebar with graph stats, entity type breakdown, embedded ingestion panel
- [x] App.tsx layout updated — Three-column: LeftPanel (w-64) | Graph (flex-1) | InfoSidebar (w-80)

### Build verification:
- Frontend: `pnpm build` passes clean (0 TypeScript errors)
- Backend: All modules import successfully
- No new npm dependencies added (Web Audio API is browser-native)

### Key decisions:
1. **Gemini Live model**: `gemini-2.0-flash-live-001` (the live-capable model)
2. **Audio format**: Frontend sends PCM16 16kHz, receives PCM 24kHz (Gemini Live's native formats)
3. **Ingestion background tasks**: REST uses FastAPI BackgroundTasks, WebSocket uses asyncio.create_task, ADK tool uses asyncio.ensure_future
4. **Progress mapping**: Phase A = 15-40%, Phase B = 45-55%, Phase C = 60-85%, storing = 88%, complete = 100%

### Open items for next session:
- [ ] User verification of all new features (run backend + frontend together)
- [ ] Apply Stitch design system when designs arrive
- [ ] End-to-end voice test with real Gemini API key
- [ ] End-to-end ingestion test (text → extraction → Neo4j → graph update)
- [ ] Canvas implementation (V1.1 — JSON component renderer)
- [ ] Cloud Run deployment setup
- [ ] ThoughtStream as standalone floating component
- [ ] Ontology view panel

---

## Session 3 — 2026-03-28 — Core Infrastructure Build (4 Parallel Agents)

**Who:** Claude Code (autonomous build session)
**Duration:** ~45 minutes (4 parallel agents)

### What was built:

#### Agent 1 — WebSocket + Graph Sync
- [x] `main.py` — WebSocket handler with initial graph data, thinking event sequence
- [x] `useWebSocket.ts` — Event routing to stores, auto-reconnect, window.sendEvent for testing
- [x] `graphStore.ts` — Reagraph-compatible types, highlighting, thinking state, color mapping
- [x] `GraphView.tsx` — 3D graph rendering from store, highlighting with dimAll, thinking overlay

#### Agent 2 — Neo4j + API
- [x] `graph/neo4j_client.py` — Async driver, 10 methods, full 15-node sample fallback
- [x] `graph/cypher_templates.py` — 10 named Cypher templates
- [x] `api/routes.py` — 9 REST endpoints with Pydantic models
- [x] `api/events.py` — Full client + server event schemas

#### Agent 3 — Extraction Pipeline
- [x] `extraction/parsers/` — PDF, URL, YouTube, text parsers + auto-detect router
- [x] `extraction/chunker.py` — Sentence-boundary text chunking
- [x] `extraction/ontology_manager.py` — Full rdflib OWL management
- [x] `extraction/pipeline.py` — Phase A/B/C with Gemini, mock mode, WebSocket progress events

#### Agent 4 — ADK Agent + Tools
- [x] `agents/context.py` — Shared module-level context
- [x] `agents/tools/query_tools.py` — 8 GraphRAG tools
- [x] `agents/tools/graph_tools.py` — 5 graph UI tools
- [x] `agents/tools/ontology_tools.py` — 9 ontology CRUD tools
- [x] `agents/tools/ingest_tools.py` — Document ingestion tool (stub, replaced in Session 4)
- [x] `agents/orchestrator.py` — 23 tools, 2 sub-agents

### Design deliverables:
- [x] `DESIGN_GUIDE.md` — Full CretaX-inspired design system (colors, typography, 8 component specs, layout, animations)
- [x] `DESIGNER_BRIEF.md` — World-class designer brief (5 screens, component sheet, aesthetic direction)
- [x] `STITCH_PROMPT.md` — Soul-first design prompt for Stitch AI (replaced overly prescriptive guides)

### Open items:
- Handed off to Session 4 for voice integration, ingestion wiring, frontend features

---

## Session 2 — 2026-03-28 — PRD v2: Deep Pipeline, Agentic Querying, Thinking UI

**Who:** [Your Name] + Claude Code
**Duration:** ~3 hours

### What was done:
- [x] Deep research: Neo4j LLM Graph Builder, neo4j-graphrag library, agentic GraphRAG, CSV auto-detection, ontology voice editing, TrustGraph thinking UI
- [x] Mapped reusable components from 3 open-source repos (neo4j-graphrag-python, trustgraph, llm-graph-builder)
- [x] Rewrote PRD to v2 with major upgrades:
  - Replaced custom extraction with `neo4j-graphrag` library as engine
  - Added full 3-phase pipeline spec (Discovery → Ontology Gen → Precision Extraction)
  - Added TrustGraph-inspired ontology subsetting (vector-embed OWL classes → find relevant subset per chunk)
  - Added agentic GraphRAG with 8 specialized query tools (not basic semantic search)
  - Added CSV → auto-detection pipeline (statistical profiling → heuristic → Gemini → auto-import)
  - Added voice-controlled ontology editing (OntologyAgent with 13 function tools + rdflib)
  - Added "Thinking Through the Graph" animation system (sequential path glow + ripple expansion + thought stream overlay)
- [x] Confirmed TrustGraph is too heavy to run directly ($180-250/mo, 12GB RAM, 34 services)
- [x] Confirmed TrustGraph's "thinking" UI is just text badges (🧠👁✅), NOT animated graph — our version is a unique innovation

### Key decisions:
1. **`neo4j-graphrag[google]`** as the extraction engine — official Neo4j library, handles chunking/extraction/dedup/writing, supports Gemini via VertexAILLM
2. **Steal patterns, not code** from TrustGraph — ontology subsetting algorithm, provenance tracking, agent query patterns
3. **Pre-built Cypher templates** for common queries (explore, path, stats) — Text2Cypher only for complex unexpected questions
4. **rdflib** for ontology management (no Java dependency, Turtle format, lightweight)
5. **3 animation modes combined** for thinking UI — sequential path glow + ripple expansion + thought stream overlay
6. **CSV auto-detection** back in scope — 3-stage pipeline (heuristic → Gemini → auto-import)
7. **Voice ontology editing** back in scope — OntologyAgent with voice commands

### Architecture changes from v1:
- Added CSVAnalysisAgent as 5th sub-agent
- Added OntologyView as new frontend panel
- Added ThoughtStream as new frontend component
- Added `useThinkingAnimation.ts` hook
- Added `ontology_subsetter.py` for TrustGraph pattern
- Phase 3 expanded from Days 8-10 to Days 8-11 (more animation work)
- WebSocket protocol expanded with 6 new `thinking_*` event types

### Open items for next session:
- [ ] Share design inspiration images for UI aesthetic
- [ ] Set up Neo4j AuraDB Free instance
- [ ] Initialize frontend with React + Vite + Tailwind + Reagraph
- [ ] Initialize backend with FastAPI + ADK + neo4j-graphrag
- [ ] Get basic WebSocket connection working
- [ ] Start Phase 1 tasks

---

## Session 1 — 2026-03-28 — Initial Setup & PRD

**Who:** [Your Name] + Claude Code
**Duration:** ~2 hours

### What was done:
- [x] Created technical PRD with full architecture, tech stack, execution plan
- [x] Researched: Gemini Live API, Google ADK, graph databases, visualization libraries, TrustGraph
- [x] Decided on tech stack:
  - Voice: Gemini Live (Multimodal Live API)
  - Agents: Google ADK (Python)
  - Graph DB: Neo4j AuraDB Free
  - Visualization: Reagraph (React, 3D)
  - Frontend: React + TypeScript + Vite + Tailwind
  - Backend: Python FastAPI + WebSocket
  - Extraction: Custom Gemini-powered ontology-guided pipeline (TrustGraph-inspired)
  - Deploy: Google Cloud Run
- [x] Set up repo folder structure
- [x] Created SESSION_LOG.md for collaboration tracking

### Key decisions:
1. **Neo4j AuraDB Free** over self-hosted options — zero cost, instant setup, 200K node limit is plenty
2. **Reagraph** over Cytoscape/Cosmograph — most React-native, built-in highlighting, modern 3D aesthetic
3. **TrustGraph-inspired custom extraction** — borrow ontology-guided approach but build with Gemini directly
4. **ADK + function calling hybrid** — ADK for orchestration, function calling for low-latency graph ops in Live sessions
5. **TrustGraph rejected for direct use** — too heavy (34+ microservices, 12GB RAM, $180-250/mo GKE) for hackathon

### Open items for next session:
- [ ] Set up Neo4j AuraDB Free instance
- [ ] Initialize frontend with React + Vite + Tailwind + Reagraph
- [ ] Initialize backend with FastAPI + ADK
- [ ] Get basic WebSocket connection working
- [ ] Create shared TypeScript/Python event types

---

---

## Session 5 — 2026-03-28 — API Keys, Animation Fix, ThoughtStream, Model Updates

**Who:** Claude Code
**Duration:** ~20 minutes

### What was done:
- [x] Set up `.env` with Gemini API key and Neo4j AuraDB credentials
- [x] Verified Gemini API works (model: `gemini-2.5-flash` for generation)
- [x] Verified Neo4j AuraDB connected (`neo4j_connected: true`)
- [x] Fixed Gemini Live model: `gemini-2.0-flash-live-001` → `gemini-3.1-flash-live-preview`
- [x] Fixed thinking animation: 5x slower (~8-10s), uses real graph data, active nodes turn WHITE
- [x] Built ThoughtStream floating panel (bottom-right, streaming reasoning steps with fade animation)
- [x] Removed inline thinking overlay from GraphView (replaced by ThoughtStream)
- [x] Fixed ingestion endpoint: split into `/api/ingest` (JSON) and `/api/ingest/file` (multipart)
- [x] Fixed React StrictMode double-mount causing WebSocket disconnect
- [x] Improved glass panel styling (opaque dark + inner highlight, not relying on backdrop-filter)

### Key decisions:
1. `gemini-2.5-flash` for text generation/extraction (works)
2. `gemini-3.1-flash-live-preview` for voice (only available live model)
3. Glass panels use opaque dark backgrounds (backdrop-filter doesn't work on WebGL canvases)

### Credentials configured:
- Gemini API: `gcloud-hackathon-fodxwx9b7vwkg` project
- Neo4j AuraDB: `b5b8bf80.databases.neo4j.io` (Free tier)
- GCP billing: linked to Trial Billing Account

### Open items:
- [ ] Verify animation visually
- [ ] Test voice conversation with real Gemini Live
- [ ] Test real extraction (not mock) with Gemini
- [ ] Check old GCP projects for unwanted charges
- [ ] Canvas (V1.1)
- [ ] Cloud Run deployment

