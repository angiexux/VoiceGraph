# VoiceGraph

**Talk to your data. See it think.**

VoiceGraph is a voice-first interactive knowledge graph that transforms unstructured data into rich, explorable knowledge graphs through natural conversation. Upload documents, PDFs, YouTube videos, or URLs — then talk to the graph using real-time voice to ask questions, explore connections, and refine the ontology, all while watching the AI reason visually across your data in 3D.

**[Live Demo](https://voicegraph-802587268683.us-central1.run.app)** | Built for the [NYC Build With AI Hackathon](https://lu.ma/NYC-Build-with-AI).

---

## Why This Exists

Knowledge is trapped in disconnected silos. Research papers, meeting notes, URLs, videos, CSVs — valuable information lives in dozens of formats across dozens of tools, and nothing connects to anything.

**Search fails at relationships.** Keyword search finds documents, not insights. "How does X relate to Y?" is unanswerable unless you manually trace connections yourself.

**RAG isn't enough.** Vanilla RAG retrieves text chunks via cosine similarity and stuffs them into a prompt. It has no concept of entities, relationships, or graph structure. It can't traverse connections, find paths, or show you the shape of what you know.

**We don't need more text answers. We need to see connections.**

---

## What Makes This Different — Not Just Another RAG App

### Standard RAG pipeline:
```
Document → chunk into 512-token pieces → embed → vector DB
Question → embed → cosine similarity → top-K chunks → stuff into prompt → LLM answers
```
Chunks are dumb. No entity awareness, no relationship tracking, no structural understanding.

### VoiceGraph pipeline:
```
Document → Phase A: schema-free entity/relationship discovery (no constraints, max recall)
         → Phase B: LLM generates formal OWL ontology from discovered patterns
         → Phase C: ontology-guided precision re-extraction + per-chunk ontology subsetting
         → Entity resolution: exact match + fuzzy match + semantic dedup
         → Result: typed, deduplicated, provenance-tracked knowledge graph in Neo4j
```

This is the difference between "find me similar text" and "build me a structured model of reality from these documents."

---

## Live Graph: DC & Energy Nexus Intelligence

VoiceGraph isn't a toy demo with 10 nodes. Our live graph contains **569 nodes and 882 edges** of real-world intelligence about the intersection of data center expansion, grid infrastructure, and community impact in NYC:

### What's in the Graph

| Category | Nodes | What |
|---|---|---|
| **Energy Experts** | 208 | Named individuals from energy trading, grid ops, policy |
| **Market Signals** | 148 | Regulatory filings, rate cases, grid alerts, policy shifts |
| **Companies** | 23 | Utilities, DC operators, energy traders, developers |
| **Facilities** | 21 | Data centers, power plants, substations, thermal networks |
| **Organizations** | 19 | NYSERDA, NY Green Bank, advocacy groups, research labs |
| **Concepts** | 16 | Thermal energy networks, 5GDHC, WSHP, grid congestion |
| **Regulations** | 14 | LL97, S9144, CLCPA, IRA Section 48, UTENJA, Justice40 |
| **Institutions** | 12 | Lincoln Hospital, Montefiore, NYCHA, DOE schools |
| **Communities** | 9 | South Bronx CD1/CD2, Mott Haven, Hunts Point, LIC, Astoria |
| **Infrastructure** | 8 | NYISO Zone J/G, Indian Point, Con Ed Steam, BQDM |
| **Data Centers** | 8 | 111 8th Ave (Google), 60 Hudson, Equinix NY4/5 |
| **Datasets** | 7 | LL84 disclosure, 311 heat complaints, NYCHA outage data |

### Demo Traversal Path

The killer demo path that makes judges lean forward:

```
South Bronx CD1 (highest energy burden in NYC)
    ↓ RATE_IMPACT_ON
Long Island City (400+ MW of pending DC interconnection)
    ↓ GRID_STRESS_FROM
NYISO Zone J (most constrained zone in NY state)
    ↓ DC_LOAD_GROWTH_TRIGGERED
S9144 Moratorium (legislative response to DC expansion)
    ↓ REGULATORY_OFFRAMP_VIA
UTENJA / Thermal Energy Networks (the solution)
    ↓ HEAT_SOURCE
Chelsea UTEN Pilot (waste heat → community heating)
    ↓ POTENTIAL_OFFTAKER_FOR
Lincoln Hospital ($2.1M/yr LL97 penalty → needs thermal solution)
```

Every node in that path is a real entity. Every edge has a description explaining *why* the connection exists. The voice agent traverses this live and narrates the connections.

### Three "Easter Egg" Connections

Non-obvious paths that no spreadsheet surfaces:

1. **Google's NYC HQ at 111 8th Avenue is in Chelsea** — the same neighborhood as the UTEN pilot recovering data center waste heat for NYCHA. A hyperscaler is literally next door to the solution.

2. **Indian Point's 2021 retirement left a 2,069 MW gap** in NYC's grid. Data centers filled that demand faster than renewables could. The grid strain communities feel today traces directly back to that retirement decision.

3. **NYC 311 heat complaint data from NYCHA buildings is public, real-time, and geocoded.** It maps directly onto communities that would benefit most from thermal energy networks. The complaint data IS the demand signal for the solution. The traversal — `311 complaint → NYCHA building → DAC designation → UTEN eligibility → potential heat offtaker` — is the most powerful path in the graph.

---

## How It Compares

### vs. ChatGPT / Gemini
GPT and Gemini are stateless text transformers. No persistent structure, no accumulated knowledge, no ability to traverse relationships.

VoiceGraph builds a **persistent, queryable knowledge structure** that grows over time. Every document adds to the graph. Connections across documents from different sources emerge automatically through entity resolution. Ask GPT "how does X from paper A relate to Y from paper B?" and it needs both papers in context. Ask VoiceGraph the same thing and it traverses a pre-built graph path.

### vs. NotebookLM
NotebookLM is excellent for conversational Q&A over a document collection. But it has zero structural awareness. It can't answer:

- "What's the shortest path between entity X and entity Y?" — requires graph traversal
- "Which entity is the most connected hub?" — requires degree centrality
- "Show me all organizations connected to people in a specific domain" — requires typed Cypher
- "What clusters exist?" — requires community detection algorithms
- "Add a new entity type and re-scan everything" — requires ontology mutation

NotebookLM also has no visualization. You can't *see* your knowledge. VoiceGraph renders a live 3D graph where you watch the AI reason — nodes light up, paths illuminate, ripples expand.

### vs. Neo4j Browser
Powerful, but requires Cypher expertise. VoiceGraph makes graph querying accessible through natural voice conversation — you speak, the agent writes and executes the Cypher.

### vs. TrustGraph
Excellent ontology-guided extraction, but 34 microservices, 12GB RAM, $180-250/mo on GKE. VoiceGraph borrows the ontology subsetting pattern but runs on Neo4j AuraDB Free ($0) + a single Cloud Run container.

---

## What It Does

1. **Ingest anything** — Drop in text, PDFs, URLs, YouTube links, or CSVs. The system parses and chunks your content automatically.

2. **Build a knowledge graph** — A 3-phase extraction pipeline discovers entities and relationships, generates a formal ontology, then re-extracts with precision using ontology-guided constraints. Entity resolution deduplicates across sources.

3. **Talk to the graph** — Ask questions by voice using Gemini Live. The AI agent selects from 8 specialized query tools — semantic search, path finding, community detection, statistical analysis — to answer naturally while highlighting relevant nodes and edges in real time.

4. **Watch it think** — As the AI reasons through your question, the graph comes alive: nodes glow along traversal paths, ripples expand from focal points, and a thought stream shows the agent's reasoning steps in real time.

5. **Refine by voice** — Edit the ontology through conversation. Add entity types, merge duplicates, adjust relationships — the agent validates changes with OWL reasoning and can selectively re-extract affected portions of the graph.

---

## Architecture

```
                          Voice (Gemini Live)
                                │
                     ┌──────────┴──────────┐
                     │   React + Three.js   │
                     │   3D Force Graph     │
                     │   + Thinking Anims   │
                     └──────────┬──────────┘
                           WebSocket
                     ┌──────────┴──────────┐
                     │  FastAPI + Google ADK │
                     │                      │
                     │  ┌── GraphQueryAgent  │──── Neo4j AuraDB
                     │  ├── IngestionAgent  │     (569 nodes, 882 edges)
                     │  ├── OntologyAgent   │
                     │  ├── CSVAnalysisAgent │
                     │  └── ExplanationAgent│
                     └─────────────────────┘
```

### 3-Phase Extraction Pipeline

| Phase | What | How |
|-------|------|-----|
| **A — Discovery** | Schema-free entity extraction | `neo4j-graphrag` with no constraints — maximum recall |
| **B — Ontology** | Generate formal OWL ontology | Gemini analyzes discovered schema → produces typed hierarchy |
| **C — Precision** | Ontology-guided re-extraction | TrustGraph-inspired subsetting — only relevant classes per chunk |

**Why this works:**
- Phase A catches everything — no entity type is missed because there are no constraints
- Phase B uses the LLM to impose human-quality semantic structure on the raw findings
- Phase C re-extracts with precision — consistent labels, proper types, no drift
- Ontology subsetting (from TrustGraph) means this scales to large ontologies without blowing context windows — all OWL classes are vector-embedded, and only the 5-10 most relevant per chunk are sent to the LLM
- Entity resolution runs three stages: exact match on canonical name, fuzzy match via rapidfuzz (0.8 threshold), and LLM-based semantic consolidation for tricky cases
- Every entity and relationship carries provenance: source document, source chunk, extraction confidence, extraction phase

### Agentic GraphRAG — 8 Specialized Query Tools

Not just semantic search — the orchestrator agent dynamically selects the right query strategy per question:

| Tool | When | How |
|------|------|-----|
| **Semantic Search** | "What do we know about grid stress?" | Vector similarity over entity embeddings |
| **Entity Explorer** | "Tell me about NYISO Zone J" | Pre-built Cypher template, 1-2 hop neighborhood traversal |
| **Path Finder** | "How does Indian Point relate to S9144?" | Shortest path via pre-built Cypher (fast + reliable) |
| **Text2Cypher** | "Which orgs have more than 5 connections?" | LLM generates Cypher from natural language + schema context |
| **Hybrid Search** | "Explain the DC energy impact landscape" | Vector search finds anchors → Cypher expands context |
| **Community Detection** | "What are the main themes?" | Leiden algorithm + LLM summaries |
| **Ontology Info** | "What entity types do we have?" | Direct OWL ontology read |
| **Graph Stats** | "How big is the graph?" | Distribution, connectivity, growth metrics |
| **Highlight Nodes** | After any query result | Lights up relevant nodes in 3D via Three.js material mutation |

Pre-built Cypher templates handle common patterns (fast + reliable). Text2Cypher is reserved for complex analytical questions the templates can't handle.

### Voice-First Architecture

Most AI tools are text-first with voice bolted on (STT → process → TTS). VoiceGraph uses Gemini Live's **native bidirectional audio streaming** — the LLM processes audio directly:

- **Function calling mid-conversation** — while you're speaking, Gemini fires graph queries, gets results, and weaves them into its spoken response
- **Voice ontology editing** — say "add a relationship type called 'mentored by'" and the OntologyAgent fires the tool, validates with rdflib, persists as OWL Turtle, and optionally triggers selective re-extraction
- **Thinking animation** — the backend emits `thinking_*` WebSocket events *during* tool execution, before the answer is ready. Three animation modes run simultaneously:
  - **Sequential path glow** — nodes light up in traversal order
  - **Ripple expansion** — concentric neighborhood reveal
  - **Thought stream** — floating panel showing reasoning steps

You watch the AI think through the graph topology. The graph animates *before* the answer arrives.

### 3D Graph Rendering

The graph isn't a flat diagram — it's a full 3D force-directed simulation rendered via Three.js:

- **Force tuning for 500+ nodes** — custom d3 charge strength (-250), link distance (120), alpha decay (0.01) to prevent the "hairball" effect
- **Type-based coloring** — 12+ node types each get distinct colors from a curated palette
- **Highlight without collapse** — highlight events mutate Three.js materials directly (color, opacity) via refs, NOT by rebuilding graphData (which would reheat the force simulation and collapse all nodes into a blob)
- **Zoom controls** — fit-to-view, zoom in/out, node dragging with pin
- **Node sizing** — scales by connection count (hub entities are visually larger)
- **Edge labels** — SpriteText labels at midpoints, directional arrows, particle animation on click

### WebSocket Event Protocol

Everything is real-time over a single WebSocket connection:
- **Audio**: bidirectional PCM chunks (16kHz up, 24kHz down)
- **Graph mutations**: `node_added`, `edge_added`, `graph_update`
- **Thinking events**: 6 event types for animation coordination
- **Highlights**: node ID + label resolution for fuzzy matching
- **Ingestion progress**: phase-by-phase status with percentage
- **Tool calls**: `tool_call_start` / `tool_call_result` for activity feed

No polling. No REST for real-time data. Frontend routes events through typed Zustand stores.

### CSV Auto-Detection

When a CSV is uploaded, a 3-stage pipeline determines optimal storage:

1. **Statistical profiling** — pandas analyzes column types, cardinality, null rates, distributions
2. **Heuristic classification** — Python rules detect ID columns, FK candidates, entity patterns (<5ms, no LLM cost)
3. **Gemini analysis** — LLM reviews stats + heuristics + sample rows → recommends graph / relational / document

Graph data gets Cypher LOAD CSV. Relational data gets SQLite with a bridge node in Neo4j. This isn't "dump everything into the graph" — it's intelligent data routing.

---

## What We Built During the Hackathon

This wasn't a wrapper around an API. Here's the actual engineering work:

### Graph Population Pipeline (not just "upload and pray")
- **Custom Neo4j population scripts** — 3 separate scripts built iteratively:
  - `populate_neo4j.py` — Base graph from SQLite + CSV sources (479 nodes, 764 edges across 13 entity types and 25 relationship types)
  - `add_uten_nodes.py` — Thermal energy network layer (legislation, UTEN pilots, technical concepts, international precedents)
  - `add_nyc_nodes.py` — NYC hyperlocal intelligence (9 communities, 8 grid infrastructure nodes, 8 data centers, 7 datasets, 6 anchor institutions, 7 financial mechanisms, 5 media/advocacy orgs)
- **Entity resolution across scripts** — MERGE-based deduplication ensures nodes like "Con Edison" or "NYSERDA" referenced in multiple scripts resolve to a single graph node
- **Rich edge descriptions** — every edge carries a human-readable `description` property explaining *why* the connection exists, not just *that* it exists

### Frontend Engineering
- **3D force graph with 500+ nodes** that doesn't collapse into a hairball — custom force parameters, direct Three.js material mutation for highlights
- **Real-time WebSocket architecture** — single connection multiplexes voice audio, graph mutations, thinking animations, ingestion progress, and tool call status
- **Type-based filtering** — toggle entity types on/off without rebuilding the force simulation
- **Responsive resize tracking** — ResizeObserver-based dimension updates for the WebGL canvas
- **Error boundary** — catches WebGL/Three.js crashes gracefully

### Backend Engineering
- **8 specialized query tools** with pre-built Cypher templates (not just Text2Cypher for everything)
- **Gemini Live integration** — bidirectional audio streaming with function calling mid-conversation
- **Multi-stage Docker build** — node:20-slim frontend build → python:3.12-slim backend, single container for Cloud Run
- **Static file serving with SPA fallback** — production frontend served from FastAPI, no separate CDN needed
- **Session affinity** for WebSocket on Cloud Run — stateful voice sessions survive load balancer routing

### Deployment
- **Single-container Cloud Run** — frontend and backend in one image, env vars for secrets
- **Artifact Registry** — proper CI/CD-ready image pipeline (not just `gcloud run deploy --source`)
- **Neo4j AuraDB Free** — $0 graph database, 200K node limit, production-grade Cypher + vector indexes

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Voice** | Gemini Live (Multimodal Live API) | Real-time bidirectional voice with function calling mid-conversation |
| **Agent Framework** | Google ADK | Multi-agent orchestration with 23 tools, Cloud Run deployment |
| **Extraction LLM** | Gemini 2.5 Flash via `VertexAILLM` | Fast, cheap, multimodal |
| **Graph Database** | Neo4j AuraDB Free | $0, 200K nodes/400K rels, Cypher + vector indexes |
| **KG Builder** | `neo4j-graphrag[google]` | Official Neo4j library — chunking, extraction, entity resolution, retrievers |
| **Ontology** | `rdflib` + OWL | Lightweight OWL manipulation (no Java), Turtle serialization |
| **3D Visualization** | react-force-graph-3d + Three.js + SpriteText | Force-directed 3D graph with direct material mutation |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind + Zustand | Type-safe, fast, reactive state management |
| **Backend** | Python FastAPI + WebSocket | Async gateway, REST API, background tasks |
| **Deployment** | Google Cloud Run (single container) | Serverless, auto-scales, session affinity for WebSocket |

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Neo4j AuraDB instance (free tier works)
- Google Cloud project with Gemini API enabled

### Setup

```bash
# Clone
git clone https://github.com/pmxlr8/VoiceGraph.git
cd VoiceGraph

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
pnpm install
```

### Environment Variables

Create `backend/.env`:

```env
GOOGLE_API_KEY=your-gemini-api-key
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

### Run Locally

```bash
# Terminal 1 — Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && pnpm dev
```

Open `http://localhost:5173` — paste some text, hit ingest, and start talking.

### Deploy to Cloud Run

```bash
# Build
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/YOUR_PROJECT/voicegraph/app:latest .

# Push
docker push us-central1-docker.pkg.dev/YOUR_PROJECT/voicegraph/app:latest

# Deploy
gcloud run deploy voicegraph \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT/voicegraph/app:latest \
  --region us-central1 --allow-unauthenticated --memory 1Gi \
  --session-affinity \
  --set-env-vars "GOOGLE_API_KEY=...,NEO4J_URI=...,NEO4J_USER=neo4j,NEO4J_PASSWORD=..."
```

---

## Project Structure

```
backend/
  main.py                  # FastAPI + WebSocket server + static SPA serving
  agents/                  # ADK orchestrator + 5 sub-agents + 23 tools
  extraction/              # 3-phase pipeline, parsers, ontology manager
  graph/                   # Neo4j client, Cypher templates
  voice/                   # Gemini Live session, tool declarations
  ingestion/               # Job manager, async ingestion flow

frontend/src/
  components/
    Graph/                 # ForceGraph3D visualization + Three.js material mutation
    VoicePanel/            # Mic capture, waveform, audio playback
    LeftPanel/             # Stats, entity types, type filtering
    InfoSidebar/           # Node details, relationships
    ThoughtStream/         # Floating AI reasoning display
    TopBar/                # Navigation, controls
    ActivityPanel/         # Tool call activity feed
    IngestModal/           # Document upload + ingestion UI
    OntologyView/          # Ontology browser
    QueryView/             # Text query interface
  stores/                  # Zustand stores (graph, voice, ingestion)
  hooks/                   # WebSocket, audio capture/playback
  types/                   # TypeScript event types

scripts/
  populate_neo4j.py        # Base graph population (479 nodes from SQLite + CSV)
  add_uten_nodes.py        # Thermal energy network layer (50+ nodes)
  add_nyc_nodes.py         # NYC hyperlocal intelligence (51 nodes, 59 edges)
```

---

## Team

- **[Pranjal Mishra](https://linkedin.com/in/pranjalmishra2002)**
- **[Bhavesh Gupta](https://linkedin.com/in/bhaveshgupta01)**
- **[Anzhelika Siui](https://linkedin.com/in/anzhelika-siui)**

---

## Acknowledgments

Built on the shoulders of open source:

- [`neo4j-graphrag-python`](https://github.com/neo4j/neo4j-graphrag-python) (Apache 2.0) — extraction pipeline, retrievers, entity resolution
- [`trustgraph`](https://github.com/trustgraph-ai/trustgraph) (Apache 2.0) — ontology subsetting pattern, provenance approach
- [`llm-graph-builder`](https://github.com/neo4j-labs/llm-graph-builder) (MIT) — YouTube parser, schema consolidation patterns
- [`react-force-graph`](https://github.com/vasturiano/react-force-graph) (MIT) — 3D force-directed graph rendering
- [`three-spritetext`](https://github.com/vasturiano/three-spritetext) (MIT) — text labels in Three.js scenes

---

## License

MIT
