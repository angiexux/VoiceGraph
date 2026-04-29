"""Hybrid retrieval: BM25 + GraphRAG fused via Reciprocal Rank Fusion (RRF)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_RRF_K = 60  # Standard constant; higher value → flatter score differences


def _rrf(rank: int) -> float:
    return 1.0 / (_RRF_K + rank + 1)


async def hybrid_search(
    query: str,
    neo4j_client: Any,
    top_k: int = 10,
) -> dict[str, Any]:
    """
    Fuse BM25 keyword results and GraphRAG vector+graph results using RRF.
    Returns re-ranked entities with a subgraph context string for the LLM.
    """
    from retrieval.bm25_retriever import get_bm25_retriever
    from retrieval.graphrag_retriever import graphrag_search

    bm25 = get_bm25_retriever()

    # Run BM25 (sync) and GraphRAG (async) concurrently
    bm25_results, graphrag_result = await asyncio.gather(
        asyncio.to_thread(bm25.search, query, top_k),
        graphrag_search(query, neo4j_client, top_k=top_k),
    )
    graphrag_anchors: list[dict[str, Any]] = graphrag_result.get("anchors", [])

    # RRF accumulation
    scores: dict[str, float] = {}
    names: dict[str, str] = {}
    descs: dict[str, str] = {}

    def _key(r: dict[str, Any]) -> str:
        return r.get("id") or r.get("name", "")

    for rank, r in enumerate(bm25_results):
        k = _key(r)
        if not k:
            continue
        scores[k] = scores.get(k, 0.0) + _rrf(rank)
        names[k] = r.get("name", "")
        descs[k] = r.get("description", "")

    for rank, r in enumerate(graphrag_anchors):
        k = _key(r)
        if not k:
            continue
        scores[k] = scores.get(k, 0.0) + _rrf(rank)
        names[k] = r.get("name", "") or names.get(k, "")
        descs[k] = r.get("description", "") or descs.get(k, "")

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    fused = [
        {
            "id": key,
            "name": names[key],
            "description": descs[key],
            "score": round(score, 4),
        }
        for key, score in ranked[:top_k]
        if names.get(key)
    ]

    return {
        "results": fused,
        "count": len(fused),
        "query": query,
        "subgraph_context": graphrag_result.get("subgraph_context", ""),
        "subgraph_nodes": graphrag_result.get("nodes", []),
        "subgraph_edges": graphrag_result.get("edges", []),
    }
