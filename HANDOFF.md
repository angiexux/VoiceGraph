# VoiceGraph — Handoff Document

## Quick Start

**Terminal 1 — Backend:**
```bash
cd ~/Desktop/KG/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8123
```

**Terminal 2 — Frontend:**
```bash
cd ~/Desktop/KG/frontend
pnpm install
pnpm dev
```

Open http://localhost:5173

---

## Current Status (Session 6)

**Working end-to-end:**

| Feature | Status | How to test |
|---------|--------|-------------|
| 3D graph rendering | Working | Open app — sample graph loads, zoom/pan/click |
| Real Gemini extraction | Working | Paste text → Extract → entities appear in graph |
| Neo4j persistence | Working | Data survives backend restarts |
| Thinking animation | Working | Type a query → nodes light up sequentially |
| WebSocket connection | Working | Green dot in voice bar = connected |
| Node details sidebar | Working | Click any node → properties + relationships |
| Ingestion (text/URL/YouTube) | Working | Left panel → paste text → Extract |
| REST API | Working | `curl http://localhost:8123/api/health` |

**Needs testing:**

| Feature | Status | Notes |
|---------|--------|-------|
| Voice conversation | Built, untested | Click mic → speak → Gemini Live responds |
| PDF ingestion | Built, untested | Upload via PDF button in left panel |
| YouTube transcript extraction | Built, untested | Paste YouTube URL → Extract |

---

## Architecture

```
Frontend (React + Vite + Tailwind)    Backend (FastAPI + Python)
├─ App.tsx (layout)                   ├─ main.py (WS + lifecycle)
├─ GraphView (Reagraph 3D)           ├─ voice/
├─ LeftPanel                          │  ├─ session.py (Gemini Live)
│  └─ IngestionPanel                  │  ├─ tool_declarations.py
├─ InfoSidebar                        │  └─ tool_executor.py
├─ VoicePanel (bottom pill)           ├─ ingestion/
├─ ThoughtStream (floating)           │  ├─ ingest.py (orchestrator)
├─ stores/ (Zustand)                  │  └─ job_manager.py
│  ├─ graphStore.ts                   ├─ extraction/
│  ├─ voiceStore.ts                   │  ├─ pipeline.py (Phase A/B/C)
│  └─ ingestionStore.ts               │  ├─ ontology_manager.py
├─ hooks/                             │  ├─ chunker.py
│  ├─ useWebSocket.ts                 │  └─ parsers/ (pdf,url,yt,text)
│  ├─ useAudioCapture.ts              ├─ agents/
│  └─ useAudioPlayback.ts             │  ├─ orchestrator.py (ADK, 23 tools)
└─ types/events.ts                    │  └─ tools/ (query,graph,ontology,ingest)
                                      ├─ graph/
                                      │  ├─ neo4j_client.py
                                      │  └─ cypher_templates.py
                                      └─ api/
                                         ├─ routes.py (9 REST endpoints)
                                         └─ events.py (Pydantic schemas)
```

## Data Flow

```
Ingest: Text/URL → Parse → Chunk → Phase A (discover entities) → Phase B (generate ontology) →
        Phase C (precision extract with Gemini) → Neo4j MERGE → WebSocket graph_update → 3D graph

Voice:  Mic → PCM16 16kHz → WS → Gemini Live → tool calls → Neo4j → WS → graph highlights
        Gemini audio → PCM 24kHz → WS → AudioBufferSourceNode → speakers

Query:  text_input → thinking animation → highlight nodes → agent response
```

## What's NOT Built Yet

| Feature | Priority | Notes |
|---------|----------|-------|
| Canvas (V1.1) | P0 — next | Voice-driven rendering surface (flowcharts, tables, timelines) |
| Cloud Run deployment | P1 | Dockerfile + `gcloud run deploy` |
| Ontology view panel | P2 | Class hierarchy tree visualization |
| CSV auto-detection | P2 | 3-stage pipeline (heuristic → Gemini → auto-import) |
| ADK agent integration for queries | P2 | Currently queries use mock animation, not real ADK agent |

## Credentials

All in `backend/.env` (not committed):
- `GOOGLE_API_KEY` — Gemini API key (project: gcloud-hackathon-fodxwx9b7vwkg)
- `NEO4J_URI` — neo4j+s://b5b8bf80.databases.neo4j.io
- `NEO4J_USERNAME` / `NEO4J_PASSWORD` — AuraDB Free tier

## Key Files

- **PRD.md** — Full technical spec
- **SESSION_LOG.md** — Build history and decisions
- **CLAUDE.md** — Instructions for Claude Code sessions
- **DESIGN_GUIDE.md** — Design system reference
