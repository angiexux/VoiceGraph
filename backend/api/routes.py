"""REST API routes for VoiceGraph knowledge graph operations."""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from ingestion.ingest import run_ingestion

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CypherQueryRequest(BaseModel):
    """Body for the arbitrary Cypher execution endpoint."""
    cypher: str = Field(..., description="Cypher query string")
    params: dict[str, Any] = Field(default_factory=dict, description="Query parameters")


class SearchRequest(BaseModel):
    """Body for the entity search endpoint."""
    query: str = Field(..., min_length=1, description="Search term")


class MergeNodeRequest(BaseModel):
    """Body for the node merge endpoint."""
    label: str = Field(..., description="Node label (e.g. Person, Concept)")
    properties: dict[str, Any] = Field(..., description="Node properties (must include 'name')")


class MergeRelationshipRequest(BaseModel):
    """Body for the relationship merge endpoint."""
    from_id: str = Field(..., description="Element ID of the source node")
    to_id: str = Field(..., description="Element ID of the target node")
    rel_type: str = Field(..., description="Relationship type (e.g. WORKS_AT)")
    properties: dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    """Body for the JSON-based ingestion endpoint."""
    source_type: str = Field("text", description="text | url | youtube | pdf")
    source: str = Field(..., description="Text content, URL, or YouTube URL")
    options: dict[str, Any] = Field(default_factory=dict, description="Extra options")


class IngestResponse(BaseModel):
    """Immediate response when an ingestion job is queued."""
    job_id: str
    status: str = "started"


class JobStatusResponse(BaseModel):
    """Status of a running or completed ingestion job."""
    id: str
    status: str
    source_type: str
    source_preview: str = ""
    progress: float
    entities_found: int
    relationships_found: int
    error: Optional[str] = None


class PathRequest(BaseModel):
    """Body for the shortest-path endpoint."""
    from_name: str
    to_name: str
    max_hops: int = Field(6, ge=1, le=20)


class NeighborhoodRequest(BaseModel):
    """Body for the neighborhood exploration endpoint."""
    name: str
    depth: int = Field(2, ge=1, le=5)


class GraphResponse(BaseModel):
    """Standard graph response with nodes and edges."""
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class StatsResponse(BaseModel):
    """Graph statistics."""
    node_count: int
    edge_count: int
    label_distribution: dict[str, int]
    relationship_distribution: dict[str, int]
    neo4j_connected: bool


class NodeDetailResponse(BaseModel):
    """Single node with neighbors."""
    id: str = ""
    labels: list[str] = []
    properties: dict[str, Any] = {}
    neighbors: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api", tags=["graph"])


def _get_client(request: Request):
    """Retrieve the Neo4jClient from app state."""
    return request.app.state.neo4j_client


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/graph", response_model=GraphResponse)
async def get_graph(request: Request):
    """Return the full graph (nodes + edges) for visualisation."""
    client = _get_client(request)
    return await client.get_full_graph()


@router.get("/graph/summary")
async def get_graph_summary(request: Request):
    """Return the top 50 nodes by degree centrality + edges between them.

    Used as the default graph view — shows the most connected concepts.
    Also returns total counts so the frontend can show "N concepts total".
    """
    client = _get_client(request)

    # Total counts
    total_rows = await client.execute_query(
        "MATCH (n) RETURN count(n) AS node_count"
    )
    total_edge_rows = await client.execute_query(
        "MATCH ()-[r]->() RETURN count(r) AS edge_count"
    )
    total_nodes = total_rows[0]["node_count"] if total_rows else 0
    total_edges = total_edge_rows[0]["edge_count"] if total_edge_rows else 0

    if total_nodes == 0:
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

    # Top 50 by degree
    top_nodes_raw = await client.execute_query(
        """
        MATCH (n)
        WITH n, size([(n)--() | 1]) AS degree
        ORDER BY degree DESC
        LIMIT 50
        RETURN elementId(n) AS id, n.name AS name, labels(n) AS labels,
               properties(n) AS properties, degree
        """
    )

    top_ids = [r["id"] for r in top_nodes_raw]
    if not top_ids:
        return {"nodes": [], "edges": [], "total_nodes": total_nodes, "total_edges": total_edges}

    # Edges between those top nodes
    edges_raw = await client.execute_query(
        """
        MATCH (a)-[r]->(b)
        WHERE elementId(a) IN $ids AND elementId(b) IN $ids
        RETURN elementId(r) AS id, type(r) AS type,
               elementId(a) AS source, elementId(b) AS target,
               properties(r) AS properties
        """,
        {"ids": top_ids},
    )

    nodes = []
    for r in top_nodes_raw:
        nodes.append({
            "id": r["id"],
            "labels": r.get("labels", []),
            "properties": r.get("properties", {}),
        })

    edges = []
    for r in edges_raw:
        edges.append({
            "id": r["id"],
            "type": r.get("type", ""),
            "source": r["source"],
            "target": r["target"],
            "properties": r.get("properties", {}),
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
    }


@router.get("/user/mind-summary")
async def get_mind_summary(request: Request):
    """Return a summary of the user's knowledge graph shape.

    Includes: community count (worldview), depth (longest chain),
    top clusters, orphan count, and domain coverage.
    """
    client = _get_client(request)

    # Total counts
    total_rows = await client.execute_query("MATCH (n) RETURN count(n) AS cnt")
    total_nodes = total_rows[0]["cnt"] if total_rows else 0

    if total_nodes < 50:
        return {
            "below_threshold": True,
            "total_nodes": total_nodes,
            "message": "Add more sources to unlock your knowledge profile.",
        }

    total_edge_rows = await client.execute_query("MATCH ()-[r]->() RETURN count(r) AS cnt")
    total_edges = total_edge_rows[0]["cnt"] if total_edge_rows else 0

    # Orphan count
    orphan_rows = await client.execute_query(
        "MATCH (n) WHERE NOT (n)--() RETURN count(n) AS cnt"
    )
    orphan_count = orphan_rows[0]["cnt"] if orphan_rows else 0

    # Entity type distribution (proxy for clusters)
    type_rows = await client.execute_query(
        """
        MATCH (n)
        RETURN labels(n)[0] AS type, count(*) AS count,
               collect(n.name)[..3] AS top_concepts
        ORDER BY count DESC
        LIMIT 10
        """
    )

    top_clusters = []
    for row in type_rows[:3]:
        top_clusters.append({
            "name": row.get("type", "Unknown"),
            "size": row.get("count", 0),
            "top_concepts": row.get("top_concepts", []),
        })

    worldview = len(type_rows)

    # Depth: longest shortest path approximation (sample-based)
    depth_rows = await client.execute_query(
        """
        MATCH (n)-[r]-()
        WITH n, count(r) AS deg
        ORDER BY deg DESC LIMIT 1
        WITH n
        MATCH path = (n)-[*1..6]-(m)
        RETURN max(length(path)) AS max_depth
        """
    )
    depth = depth_rows[0]["max_depth"] if depth_rows and depth_rows[0].get("max_depth") else 0

    # Coverage: compare against expected types for user domain
    from user.profile import get_profile
    profile = get_profile()
    domain = profile.get("domain", "")

    from agents.tools.blind_spot import _get_expected_types
    expected = _get_expected_types(domain)
    present_types = {row["type"] for row in type_rows if row.get("type")}
    present_count = sum(1 for t in expected if t in present_types)
    coverage_pct = round((present_count / len(expected)) * 100) if expected else 0

    return {
        "worldview": worldview,
        "depth": depth,
        "top_clusters": top_clusters,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "orphan_count": orphan_count,
        "coverage_percent": coverage_pct,
    }


@router.get("/graph/node/{node_id:path}", response_model=NodeDetailResponse)
async def get_node(node_id: str, request: Request):
    """Return a single node with all properties and neighbours."""
    client = _get_client(request)
    data = await client.get_node_details(node_id)
    if not data:
        raise HTTPException(status_code=404, detail="Node not found")
    return data


@router.post("/graph/query")
async def execute_cypher(body: CypherQueryRequest, request: Request):
    """Execute an arbitrary Cypher query and return the results."""
    client = _get_client(request)
    try:
        rows = await client.execute_query(body.cypher, body.params)
        return {"results": rows, "count": len(rows)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/stats", response_model=StatsResponse)
async def get_stats(request: Request):
    """Return summary statistics about the knowledge graph."""
    client = _get_client(request)
    return await client.get_stats()


@router.post("/search")
async def search_entities(body: SearchRequest, request: Request):
    """Search entities by name (case-insensitive fuzzy match)."""
    client = _get_client(request)
    results = await client.find_entity(body.query)
    return {"results": results, "count": len(results)}


@router.post("/graph/path")
async def find_path(body: PathRequest, request: Request):
    """Find the shortest path between two named entities."""
    client = _get_client(request)
    return await client.shortest_path(body.from_name, body.to_name, body.max_hops)


@router.post("/graph/neighborhood")
async def explore_neighborhood(body: NeighborhoodRequest, request: Request):
    """Explore the neighbourhood of a named entity up to N hops."""
    client = _get_client(request)
    return await client.explore_neighborhood(body.name, body.depth)


@router.post("/graph/node")
async def merge_node(body: MergeNodeRequest, request: Request):
    """Merge (create or update) a node by name + label."""
    client = _get_client(request)
    if "name" not in body.properties:
        raise HTTPException(status_code=422, detail="properties must include 'name'")
    node_id = await client.merge_node(body.label, body.properties)

    # Broadcast to all WebSocket clients
    broadcast_fn = _get_broadcast_fn(request)
    if broadcast_fn:
        await broadcast_fn({
            "type": "node_added",
            "node": {
                "id": node_id,
                "label": body.properties.get("name", ""),
                "type": body.label,
                "properties": body.properties,
            },
        })

    return {"id": node_id, "status": "merged"}


@router.post("/graph/relationship")
async def merge_relationship(body: MergeRelationshipRequest, request: Request):
    """Merge (create or update) a relationship between two nodes."""
    client = _get_client(request)
    rel_id = await client.merge_relationship(
        body.from_id, body.to_id, body.rel_type, body.properties
    )

    # Broadcast to all WebSocket clients
    broadcast_fn = _get_broadcast_fn(request)
    if broadcast_fn:
        await broadcast_fn({
            "type": "edge_added",
            "edge": {
                "id": rel_id,
                "source": body.from_id,
                "target": body.to_id,
                "label": body.rel_type,
                "properties": body.properties,
            },
        })

    return {"id": rel_id, "status": "merged"}


# ---------------------------------------------------------------------------
# Ingestion endpoints
# ---------------------------------------------------------------------------


def _get_job_manager(request: Request):
    """Retrieve the JobManager from app state."""
    return request.app.state.job_manager


def _get_broadcast_fn(request: Request):
    """Retrieve the broadcast function from app state."""
    return request.app.state.broadcast_fn


def _get_ontology_manager(request: Request):
    """Retrieve the OntologyManager from app state (may be None)."""
    return getattr(request.app.state, "ontology_manager", None)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: Request,
    background_tasks: BackgroundTasks,
    body: IngestRequest,
):
    """Ingest text/URL/YouTube into the knowledge graph via JSON body."""
    job_manager = _get_job_manager(request)
    neo4j_client = _get_client(request)
    ontology_manager = _get_ontology_manager(request)
    broadcast_fn = _get_broadcast_fn(request)

    job = job_manager.create_job(source_type=body.source_type, source_preview=body.source[:200])

    background_tasks.add_task(
        _run_ingestion_task,
        job.id,
        body.source_type,
        body.source,
        job_manager,
        neo4j_client,
        ontology_manager,
        broadcast_fn,
    )

    return IngestResponse(job_id=job.id, status="started")


@router.post("/ingest/file", response_model=IngestResponse)
async def ingest_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_type: str = Form(default="pdf"),
):
    """Ingest a PDF file upload into the knowledge graph."""
    import tempfile, os

    job_manager = _get_job_manager(request)
    neo4j_client = _get_client(request)
    ontology_manager = _get_ontology_manager(request)
    broadcast_fn = _get_broadcast_fn(request)

    suffix = os.path.splitext(file.filename or "upload")[1] or ".pdf"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    file_bytes = await file.read()
    tmp.write(file_bytes)
    tmp.close()

    job = job_manager.create_job(source_type=source_type, source_preview=file.filename or "uploaded file")

    background_tasks.add_task(
        _run_ingestion_task,
        job.id,
        source_type,
        tmp.name,
        job_manager,
        neo4j_client,
        ontology_manager,
        broadcast_fn,
    )

    return IngestResponse(job_id=job.id, status="started")


async def _run_ingestion_task(
    job_id: str,
    source_type: str,
    content: str,
    job_manager,
    neo4j_client,
    ontology_manager,
    broadcast_fn,
) -> None:
    """Wrapper that runs the async ingestion in the existing event loop."""
    await run_ingestion(
        job_id=job_id,
        source_type=source_type,
        content=content,
        job_manager=job_manager,
        neo4j_client=neo4j_client,
        ontology_manager=ontology_manager,
        broadcast_fn=broadcast_fn,
    )


@router.get("/ingest/{job_id}", response_model=JobStatusResponse)
async def get_ingest_status(job_id: str, request: Request):
    """Return the current status of an ingestion job."""
    job_manager = _get_job_manager(request)
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job.to_dict()


@router.get("/user/blind-spots")
async def get_blind_spots(request: Request):
    """Return blind spots: orphan nodes and underrepresented entity types."""
    client = _get_client(request)
    from user.profile import get_profile
    profile = get_profile()
    domain = profile.get("domain", "")

    try:
        from agents.tools.blind_spot import detect_blind_spots
        return await detect_blind_spots(domain)
    except Exception as exc:
        logger.warning("Blind spot detection failed: %s", exc)
        return {"orphan_nodes": [], "orphan_count": 0, "missing_types": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# Test / Demo endpoints
# ---------------------------------------------------------------------------

_DEMO_TYPES = ["Person", "Organization", "Concept", "Event", "Location",
               "Technology", "Theory", "Field", "Method", "Award"]
_DEMO_RELS = ["related_to", "works_at", "developed", "located_in", "part_of",
              "influenced", "collaborated_with", "studied", "founded", "won"]
_DEMO_NAMES = {
    "Person": ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank",
               "Ivy", "Jack", "Karen", "Leo", "Mona", "Nick", "Olivia", "Paul",
               "Quinn", "Rita", "Sam", "Tina", "Uma", "Vic", "Wendy", "Xander"],
    "Organization": ["MIT", "Google", "NASA", "CERN", "OpenAI", "Stanford", "DeepMind",
                     "SpaceX", "Apple", "Meta", "Microsoft", "Amazon", "Tesla", "IBM"],
    "Concept": ["Entropy", "Consciousness", "Emergence", "Symmetry", "Causality",
                "Complexity", "Abstraction", "Recursion", "Duality", "Resonance"],
    "Event": ["Big Bang", "Renaissance", "Industrial Revolution", "Moon Landing",
              "World War II", "French Revolution", "Cold War", "Digital Revolution"],
    "Location": ["New York", "London", "Tokyo", "Paris", "Berlin", "Mumbai", "Sydney",
                 "Toronto", "Seoul", "Beijing", "Singapore", "Dubai", "Moscow", "Rome"],
    "Technology": ["Neural Networks", "Blockchain", "Quantum Computing", "CRISPR",
                   "5G", "Fusion Energy", "AR/VR", "Robotics", "IoT", "Edge Computing"],
    "Theory": ["Relativity", "Quantum Mechanics", "Evolution", "Game Theory",
               "Information Theory", "Chaos Theory", "String Theory", "Set Theory"],
    "Field": ["Physics", "Biology", "Computer Science", "Mathematics", "Philosophy",
              "Economics", "Neuroscience", "Chemistry", "Linguistics", "Psychology"],
    "Method": ["Gradient Descent", "Monte Carlo", "Bayesian Inference", "PCA",
               "Fourier Transform", "A* Search", "Dynamic Programming", "Backpropagation"],
    "Award": ["Nobel Prize", "Turing Award", "Fields Medal", "Wolf Prize",
              "Breakthrough Prize", "Abel Prize", "Pulitzer Prize", "Grammy"],
}


@router.get("/test/generate")
async def generate_test_graph(n: int = 500):
    """Generate a synthetic graph with n nodes for stress testing.

    Usage: GET /api/test/generate?n=1000
    Returns the graph directly (does NOT write to Neo4j).
    Load it on the frontend by calling setGraph() with the result.
    """
    nodes = []
    for i in range(n):
        t = random.choice(_DEMO_TYPES)
        names = _DEMO_NAMES[t]
        base_name = random.choice(names)
        name = f"{base_name} {i}" if i >= len(names) else base_name
        nodes.append({
            "id": f"test-{i}",
            "label": name,
            "type": t,
            "properties": {"name": name, "entity_type": t},
        })

    # Create edges: ~2.5x nodes for a rich graph
    edge_count = int(n * 2.5)
    edges = []
    for j in range(edge_count):
        src = random.randint(0, n - 1)
        tgt = random.randint(0, n - 1)
        if src == tgt:
            tgt = (tgt + 1) % n
        edges.append({
            "id": f"test-e-{j}",
            "source": f"test-{src}",
            "target": f"test-{tgt}",
            "label": random.choice(_DEMO_RELS),
            "type": random.choice(_DEMO_RELS),
            "properties": {},
        })

    return {"nodes": nodes, "edges": edges, "count": {"nodes": len(nodes), "edges": len(edges)}}
