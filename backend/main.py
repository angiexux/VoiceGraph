"""VoiceGraph Backend — FastAPI application entry point."""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import router as graph_router
from user.profile import router as user_router
from graph.neo4j_client import Neo4jClient
from ingestion.job_manager import JobManager
from extraction.ontology_manager import OntologyManager
from agents import context as agent_ctx
from voice.session import VoiceSession

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connected client tracking
# ---------------------------------------------------------------------------

connected_clients: list[WebSocket] = []

# Map each WebSocket to its active VoiceSession (if any)
voice_sessions: dict[WebSocket, VoiceSession] = {}


# ---------------------------------------------------------------------------
# Sample graph data (AI/ML knowledge graph)
# ---------------------------------------------------------------------------

SAMPLE_NODES = [
    {"id": "ai", "label": "Artificial Intelligence", "type": "Field", "properties": {"description": "The simulation of human intelligence by machines"}},
    {"id": "ml", "label": "Machine Learning", "type": "Field", "properties": {"description": "Subset of AI that learns from data"}},
    {"id": "dl", "label": "Deep Learning", "type": "Method", "properties": {"description": "ML using neural networks with many layers"}},
    {"id": "nn", "label": "Neural Networks", "type": "Technology", "properties": {"description": "Computing systems inspired by biological neural networks"}},
    {"id": "transformer", "label": "Transformer", "type": "Architecture", "properties": {"description": "Attention-based architecture for sequence modeling"}},
    {"id": "nlp", "label": "Natural Language Processing", "type": "Field", "properties": {"description": "AI subfield dealing with human language"}},
    {"id": "cv", "label": "Computer Vision", "type": "Field", "properties": {"description": "AI subfield for visual understanding"}},
    {"id": "gpt", "label": "GPT-4", "type": "Model", "properties": {"description": "Generative Pre-trained Transformer by OpenAI"}},
    {"id": "openai", "label": "OpenAI", "type": "Organization", "properties": {"description": "AI research organization"}},
    {"id": "google", "label": "Google DeepMind", "type": "Organization", "properties": {"description": "AI research lab at Google"}},
    {"id": "hinton", "label": "Geoffrey Hinton", "type": "Person", "properties": {"description": "Pioneer of deep learning"}},
    {"id": "attention", "label": "Attention Mechanism", "type": "Concept", "properties": {"description": "Mechanism allowing models to focus on relevant parts of input"}},
    {"id": "rl", "label": "Reinforcement Learning", "type": "Method", "properties": {"description": "Learning through interaction with an environment"}},
    {"id": "alphago", "label": "AlphaGo", "type": "Model", "properties": {"description": "First AI to defeat a world champion at Go"}},
    {"id": "stanford", "label": "Stanford University", "type": "Organization", "properties": {"description": "Leading AI research university"}},
]

SAMPLE_EDGES = [
    {"id": "e1", "source": "ai", "target": "ml", "label": "includes"},
    {"id": "e2", "source": "ml", "target": "dl", "label": "includes"},
    {"id": "e3", "source": "dl", "target": "nn", "label": "uses"},
    {"id": "e4", "source": "nn", "target": "transformer", "label": "variant_of"},
    {"id": "e5", "source": "transformer", "target": "nlp", "label": "applied_to"},
    {"id": "e6", "source": "transformer", "target": "attention", "label": "based_on"},
    {"id": "e7", "source": "ai", "target": "nlp", "label": "subfield"},
    {"id": "e8", "source": "ai", "target": "cv", "label": "subfield"},
    {"id": "e9", "source": "gpt", "target": "transformer", "label": "based_on"},
    {"id": "e10", "source": "openai", "target": "gpt", "label": "created"},
    {"id": "e11", "source": "hinton", "target": "dl", "label": "pioneered"},
    {"id": "e12", "source": "hinton", "target": "google", "label": "worked_at"},
    {"id": "e13", "source": "google", "target": "alphago", "label": "developed"},
    {"id": "e14", "source": "alphago", "target": "rl", "label": "uses"},
    {"id": "e15", "source": "ml", "target": "rl", "label": "includes"},
    {"id": "e16", "source": "stanford", "target": "ai", "label": "researches"},
    {"id": "e17", "source": "dl", "target": "cv", "label": "applied_to"},
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


async def send_event(ws: WebSocket, event: dict[str, Any]) -> None:
    """Serialize and send a server event as JSON."""
    try:
        await ws.send_text(json.dumps(event))
    except Exception:
        logger.exception("Failed to send event to client")


async def broadcast_event(event: dict[str, Any], exclude: WebSocket | None = None) -> None:
    """Send an event to all connected clients, optionally excluding one."""
    for client in connected_clients:
        if client is not exclude:
            await send_event(client, event)


def _normalize_node(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert a Neo4j-style node dict to the frontend GraphNode format."""
    # Already in frontend format (has 'label' key)
    if "label" in raw:
        return raw
    # Neo4j format: {id, labels: [...], properties: {name, ...}}
    labels_list = raw.get("labels", [])
    props = raw.get("properties", {})
    node_type = labels_list[0] if labels_list else "Concept"
    # Build a human-readable label from properties
    label = props.get("name") or props.get("label") or props.get("title")
    if not label:
        # Signal nodes: use truncated snippet
        snippet = props.get("snippet") or props.get("summary") or props.get("description")
        if snippet:
            label = snippet[:50] + ("..." if len(snippet) > 50 else "")
        # Order nodes: side + order_id
        elif props.get("order_id"):
            side = props.get("side", "")
            label = f"{side} {props['order_id']}".strip()
        else:
            label = node_type
    return {
        "id": raw["id"],
        "label": label,
        "type": node_type,
        "properties": props,
    }


def _normalize_edge(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert a Neo4j-style edge dict to the frontend GraphEdge format."""
    # Already in frontend format (has 'label' key)
    if "label" in raw:
        return raw
    # Neo4j format: {id, type: "REL_TYPE", source, target, properties}
    return {
        "id": raw["id"],
        "source": raw["source"],
        "target": raw["target"],
        "label": raw.get("type", "related_to").lower(),
        "properties": raw.get("properties", {}),
    }


async def send_initial_graph(ws: WebSocket, app: FastAPI) -> None:
    """Send the full graph to a newly connected client."""
    client = getattr(app.state, "neo4j_client", None)
    if client is not None:
        graph = await client.get_full_graph()
        raw_nodes = graph["nodes"]
        raw_edges = graph["edges"]
        nodes = [_normalize_node(n) for n in raw_nodes]
        edges = [_normalize_edge(e) for e in raw_edges]
    else:
        nodes = SAMPLE_NODES
        edges = SAMPLE_EDGES
    # If Neo4j is connected but empty, use sample data so the graph isn't blank
    if not nodes:
        nodes = SAMPLE_NODES
        edges = SAMPLE_EDGES
    await send_event(ws, {
        "type": "graph_update",
        "nodes": nodes,
        "edges": edges,
    })


async def handle_text_input(ws: WebSocket, event: dict[str, Any]) -> None:
    """Handle a text_input event: run real query tools against Neo4j."""
    from agents.tools.query_tools import (
        search_concepts, explore_entity, find_path,
        get_graph_stats, deep_search, get_communities, get_ontology_info,
    )
    from agents.tools.graph_tools import highlight_nodes, add_node, add_relationship, remove_node

    text = event.get("text", "").strip()
    if not text:
        return

    # Echo user transcript
    await send_event(ws, {"type": "transcript", "role": "user", "text": text})

    # Thinking start
    await send_event(ws, {"type": "thinking_start", "query": text})

    text_lower = text.lower()

    try:
        # Route to the right tool based on query intent
        result_nodes: list[str] = []
        result_edges: list[str] = []
        response_text = ""

        # ---- Mutation: add node ----
        if text_lower.startswith(("add ", "create ")) and " as " in text_lower:
            # Pattern: "add Einstein as Person" or "create Quantum Computing as Concept"
            parts = text.split(" as ", 1)
            name = parts[0]
            for prefix in ["add ", "create "]:
                if name.lower().startswith(prefix):
                    name = name[len(prefix):]
            name = name.strip().strip('"\'')
            entity_type = parts[1].strip().strip('"\'.')
            await send_event(ws, {"type": "thinking_step", "step": f"Adding {name} as {entity_type}...", "icon": "➕"})
            result = await add_node(name=name, entity_type=entity_type)
            node_id = result.get("node_id", "")
            if node_id:
                result_nodes = [node_id]
            response_text = result.get("message", f"Added {name}.")

        # ---- Mutation: add relationship ----
        elif text_lower.startswith(("connect ", "link ", "relate ")) or (" connects to " in text_lower) or (" link to " in text_lower):
            # Pattern: "connect Einstein to Physics as CONTRIBUTED_TO"
            # or "connect Einstein to Physics" (defaults to RELATED_TO)
            cleaned = text
            for prefix in ["connect ", "link ", "relate "]:
                if cleaned.lower().startswith(prefix):
                    cleaned = cleaned[len(prefix):]
            # Split on " to "
            rel_type = "RELATED_TO"
            if " as " in cleaned:
                cleaned, rel_type = cleaned.rsplit(" as ", 1)
                rel_type = rel_type.strip().strip('"\'.')
            parts = cleaned.split(" to ", 1)
            if len(parts) == 2:
                source = parts[0].strip().strip('"\'')
                target = parts[1].strip().strip('"\'.')
                await send_event(ws, {"type": "thinking_step", "step": f"Connecting {source} → {target}...", "icon": "🔗"})
                result = await add_relationship(source_name=source, target_name=target, relationship_type=rel_type)
                response_text = result.get("message", f"Connected {source} to {target}.")
            else:
                response_text = "To connect entities, use: 'connect [entity A] to [entity B]'"

        # ---- Mutation: remove/delete node ----
        elif text_lower.startswith(("delete ", "remove ")):
            name = text
            for prefix in ["delete ", "remove "]:
                if name.lower().startswith(prefix):
                    name = name[len(prefix):]
            name = name.strip().strip('"\'.')
            await send_event(ws, {"type": "thinking_step", "step": f"Removing {name}...", "icon": "🗑"})
            result = await remove_node(name=name)
            response_text = result.get("message", f"Removed {name}.")

        # ---- Query: stats ----
        elif any(w in text_lower for w in ["stat", "how many", "how big", "overview", "size"]):
            await send_event(ws, {"type": "thinking_step", "step": "Fetching graph statistics...", "icon": "📊"})
            stats = await get_graph_stats()
            nc = stats.get("node_count", 0)
            ec = stats.get("edge_count", 0)
            top = stats.get("most_connected", [])[:5]
            top_names = [t.get("name", "?") for t in top]
            response_text = (
                f"The graph has {nc} entities and {ec} relationships. "
                f"Most connected: {', '.join(top_names)}." if top_names
                else f"The graph has {nc} entities and {ec} relationships."
            )

        elif any(w in text_lower for w in ["connect", "path", "between", "link"]):
            # Try to extract two entity names from the query
            # Simple heuristic: look for quoted names or split on "and"/"to"
            parts = None
            for sep in [" and ", " to ", " with "]:
                if sep in text_lower:
                    parts = text.split(sep, 1) if sep in text else text_lower.split(sep, 1)
                    break
            if parts and len(parts) == 2:
                a, b = parts[0].strip().strip('"\''), parts[1].strip().strip('"\'?.')
                # Clean common prefixes and suffixes
                for prefix in ["how does ", "how do ", "how is ", "find path ", "path between ",
                               "connection between ", "what connects ", "what links "]:
                    if a.lower().startswith(prefix):
                        a = a[len(prefix):]
                # Clean trailing verbs from entity A (e.g. "Einstein connect" -> "Einstein")
                for suffix in [" connect", " link", " relate", " path"]:
                    if a.lower().endswith(suffix):
                        a = a[:len(a) - len(suffix)]
                a = a.strip()
                b = b.strip()
                await send_event(ws, {"type": "thinking_step", "step": f"Finding path: {a} → {b}...", "icon": "🔗"})
                path_result = await find_path(a, b)
                if path_result.get("found"):
                    response_text = f"Found a path connecting '{a}' to '{b}' through {len(path_result.get('path', []))} steps."
                else:
                    response_text = f"No direct path found between '{a}' and '{b}'. They may not be connected in the graph."
            else:
                await send_event(ws, {"type": "thinking_step", "step": "Searching...", "icon": "🔍"})
                sr = await search_concepts(text, top_k=10)
                results = sr.get("results", [])
                result_nodes = [r.get("id", "") for r in results if r.get("id")]
                names = [r.get("name", "") for r in results[:5]]
                response_text = f"Found {len(results)} related entities: {', '.join(names)}." if names else "No matching entities found."

        elif any(w in text_lower for w in ["theme", "communit", "cluster", "main topic"]):
            await send_event(ws, {"type": "thinking_step", "step": "Analyzing communities...", "icon": "🏘"})
            comm = await get_communities()
            communities = comm.get("communities", [])[:5]
            desc = "; ".join(f"{c.get('theme', '?')} ({c.get('entity_count', 0)} entities)" for c in communities)
            response_text = f"Main themes: {desc}." if desc else "No community data available."

        elif any(w in text_lower for w in ["ontology", "types", "schema", "what kind"]):
            await send_event(ws, {"type": "thinking_step", "step": "Loading ontology...", "icon": "📋"})
            onto = await get_ontology_info()
            if "ontology" in onto:
                response_text = "Ontology loaded. I can see the entity types and relationship types defined in the schema."
            else:
                types_list = onto.get("entity_types", [])
                type_names = [", ".join(t.get("types", [])) for t in types_list[:8]]
                response_text = f"Entity types in the graph: {', '.join(type_names)}." if type_names else "No ontology data available."

        # ---- Concept expansion ----
        elif any(phrase in text_lower for phrase in [
            "what do i know about", "tell me about", "what is", "who is",
            "explore", "detail", "show me", "how does", "in my notes",
        ]):
            # Entity exploration — extract the entity name
            entity = text
            for prefix in ["tell me about ", "what is ", "who is ", "explore ", "show me ", "details on ", "detail "]:
                if text_lower.startswith(prefix):
                    entity = text[len(prefix):].strip().strip('"\'?.')
                    break
            await send_event(ws, {"type": "thinking_step", "step": f"Exploring: {entity}...", "icon": "🔎"})
            exp = await explore_entity(entity)
            nodes = exp.get("nodes", [])
            edges = exp.get("edges", [])
            result_nodes = [n.get("id", "") for n in nodes if n.get("id")]
            result_edges = [e.get("id", "") for e in edges if e.get("id")]
            if nodes:
                # Build rich response with relationship context
                conn_names = [n.get("name", "") for n in nodes
                              if n.get("name", "").lower() != entity.lower()][:6]
                rel_types = list({e.get("type", "") for e in edges if e.get("type")})[:4]
                parts = [f"{entity} has {len(nodes)} connections"]
                if conn_names:
                    parts.append(f"Connected to: {', '.join(conn_names)}")
                if rel_types:
                    parts.append(f"Relationships: {', '.join(rel_types)}")
                response_text = ". ".join(parts) + "."
            else:
                response_text = f"No data found for '{entity}'. Try a different search term."

        else:
            # Default: search then auto-explore top result
            await send_event(ws, {"type": "thinking_step", "step": f"Searching for: {text}...", "icon": "🔍"})
            sr = await search_concepts(text, top_k=10)
            results = sr.get("results", [])

            # Deduplicate by case-insensitive name
            seen_names: set[str] = set()
            deduped: list[dict] = []
            for r in results:
                name_lower = r.get("name", "").lower()
                if name_lower not in seen_names:
                    seen_names.add(name_lower)
                    deduped.append(r)
            results = deduped

            result_nodes = [r.get("id", "") for r in results if r.get("id")]
            if results:
                # Auto-explore the best match for richer response
                best = results[0]
                best_name = best.get("name", "")
                best_types = best.get("types", [])
                best_type = best_types[0] if best_types else "Entity"
                best_desc = best.get("description", "")

                await send_event(ws, {"type": "thinking_step", "step": f"Exploring: {best_name}...", "icon": "🔎"})
                exp = await explore_entity(best_name)
                neighbors = exp.get("nodes", [])
                edges = exp.get("edges", [])
                if neighbors:
                    result_nodes = [n.get("id", "") for n in neighbors if n.get("id")]
                    result_edges = [e.get("id", "") for e in edges if e.get("id")]

                # Build a rich response
                parts = [f"{best_name} ({best_type})"]
                if best_desc:
                    parts.append(best_desc)
                if neighbors:
                    conn_names = [n.get("name", "") for n in neighbors if n.get("name", "").lower() != best_name.lower()][:5]
                    if conn_names:
                        parts.append(f"Connected to: {', '.join(conn_names)}")
                if len(results) > 1:
                    other_names = [r.get("name", "") for r in results[1:4]]
                    parts.append(f"Also found: {', '.join(other_names)}")
                response_text = ". ".join(parts) + "."
            else:
                response_text = f"No results found for '{text}'. Try a different search term or ingest more data."

        # Highlight result nodes on graph
        if result_nodes:
            highlight_nodes(node_ids=result_nodes, edge_ids=result_edges)

        # Thinking complete
        await send_event(ws, {
            "type": "thinking_complete",
            "resultNodeIds": result_nodes,
            "resultEdgeIds": result_edges,
        })

        # Agent response
        await send_event(ws, {
            "type": "transcript",
            "role": "agent",
            "text": response_text,
        })

    except Exception as exc:
        logger.exception("Query failed: %s", exc)
        await send_event(ws, {"type": "thinking_complete", "resultNodeIds": [], "resultEdgeIds": []})
        await send_event(ws, {
            "type": "transcript",
            "role": "agent",
            "text": f"Sorry, I encountered an error processing your query: {exc}",
        })


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of long-lived resources."""
    # Neo4j
    client = Neo4jClient()
    await client.connect()
    app.state.neo4j_client = client
    logger.info("Neo4j client ready (connected=%s)", client.available)

    # Ingestion job manager
    app.state.job_manager = JobManager()

    # Ontology manager (shared instance for extraction)
    app.state.ontology_manager = OntologyManager()

    # Broadcast function — accessible by routes and ingestion tasks
    app.state.broadcast_fn = broadcast_event

    # Populate shared agent context so ADK tools can access resources
    agent_ctx.neo4j_client = client
    agent_ctx.ontology_manager = app.state.ontology_manager
    agent_ctx.ws_broadcast = broadcast_event

    yield
    await client.close()


app = FastAPI(
    title="VoiceGraph API",
    description="Knowledge-graph voice assistant backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

app.include_router(graph_router)
app.include_router(user_router)


# ---------------------------------------------------------------------------
# Health check (standalone — not part of the graph router)
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    """Return service health status."""
    client = getattr(app.state, "neo4j_client", None)
    return {
        "status": "ok",
        "service": "voicegraph-backend",
        "neo4j_connected": client.available if client else False,
    }


# ---------------------------------------------------------------------------
# Static frontend (production — served from built frontend in /app/static)
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

    # SPA fallback — serve index.html for all non-API/WS routes
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Check if the file exists in static dir
        file_path = STATIC_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))


# ---------------------------------------------------------------------------
# WebSocket endpoint — voice interaction channel
# ---------------------------------------------------------------------------


@app.websocket("/ws/voice")
async def voice_ws(websocket: WebSocket):
    """Accept a WebSocket connection for real-time voice interaction.

    Protocol:
      - Client sends JSON events (see api/events.py for schemas).
      - Server responds with appropriate server events.
    """
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info("Client connected. Total clients: %d", len(connected_clients))

    try:
        # Send initial graph data to the newly connected client
        await send_initial_graph(websocket, app)

        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                await send_event(websocket, {
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            event_type = event.get("type")

            if event_type == "text_input":
                # If a voice session is active, forward text to Gemini
                voice_session = voice_sessions.get(websocket)
                if voice_session and voice_session.active:
                    text = event.get("text", "")
                    await send_event(websocket, {
                        "type": "transcript",
                        "role": "user",
                        "text": text,
                    })
                    await voice_session.send_text(text)
                else:
                    await handle_text_input(websocket, event)

            elif event_type == "start_voice":
                # Reuse existing session if still alive, otherwise create new
                existing = voice_sessions.get(websocket)
                if existing and existing.active:
                    # Session already running — just confirm
                    await send_event(websocket, {
                        "type": "voice_ready",
                        "message": "Voice session active.",
                    })
                else:
                    # Clean up dead session if any
                    if existing:
                        try:
                            await existing.close()
                        except Exception:
                            pass

                    async def _make_sender(ws: WebSocket):
                        async def _send(evt: dict[str, Any]) -> None:
                            await send_event(ws, evt)
                        return _send

                    sender = await _make_sender(websocket)
                    session = VoiceSession(send_event=sender)
                    voice_sessions[websocket] = session
                    await session.start()

            elif event_type == "stop_voice":
                # DON'T destroy the session — just acknowledge
                # The session stays alive for continuous conversation
                await send_event(websocket, {
                    "type": "voice_stopped",
                    "message": "Mic paused. Session still active.",
                })

            elif event_type == "interrupt_voice":
                # Interrupt: close the current session and restart fresh
                # This is the only way to stop Gemini mid-response
                voice_session = voice_sessions.get(websocket)
                if voice_session and voice_session.active:
                    logger.info("Interrupting voice session")
                    history = list(voice_session._conversation_history)
                    await voice_session.close()
                    del voice_sessions[websocket]
                    # Brief pause to let the old session fully tear down
                    await asyncio.sleep(0.3)
                    # Start a fresh session with conversation history preserved
                    sender = await _make_sender(websocket)
                    new_session = VoiceSession(send_event=sender)
                    new_session._conversation_history = history
                    voice_sessions[websocket] = new_session
                    await new_session.start()
                await send_event(websocket, {
                    "type": "voice_interrupted",
                    "message": "Interrupted. Listening...",
                })

            elif event_type == "audio_chunk":
                # Forward audio to the active voice session
                voice_session = voice_sessions.get(websocket)
                if voice_session and voice_session.active:
                    audio_data = event.get("data", "")
                    if audio_data:
                        await voice_session.send_audio(audio_data)
                else:
                    logger.debug("Received audio_chunk but no active voice session")

            elif event_type == "ingest_document":
                # Handle inline ingestion request via WebSocket
                source = event.get("source", "")
                source_type = event.get("source_type", "text")
                if not source:
                    await send_event(websocket, {
                        "type": "error",
                        "message": "ingest_document requires a 'source' field.",
                    })
                else:
                    from ingestion.ingest import run_ingestion
                    jm = app.state.job_manager
                    job = jm.create_job(source_type=source_type, source_preview=source[:200])
                    await send_event(websocket, {
                        "type": "ingestion_status",
                        "job_id": job.id,
                        "status": "started",
                        "progress": 0.0,
                    })
                    # Run in background so the WS loop stays responsive
                    asyncio.create_task(run_ingestion(
                        job_id=job.id,
                        source_type=source_type,
                        content=source,
                        job_manager=jm,
                        neo4j_client=app.state.neo4j_client,
                        ontology_manager=app.state.ontology_manager,
                        broadcast_fn=broadcast_event,
                    ))

            elif event_type == "graph_action":
                # Handle graph actions (expand, collapse, pin)
                action = event.get("action")
                node_id = event.get("nodeId")
                logger.info("Graph action: %s on node %s", action, node_id)
                await send_event(websocket, {
                    "type": "highlight",
                    "nodeIds": [node_id] if node_id else [],
                    "edgeIds": [],
                })

            else:
                await send_event(websocket, {
                    "type": "error",
                    "message": f"Unknown event type: {event_type}",
                })

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception:
        logger.exception("WebSocket error")
    finally:
        # Clean up voice session if active
        voice_session = voice_sessions.pop(websocket, None)
        if voice_session:
            await voice_session.close()

        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info("Remaining clients: %d", len(connected_clients))
