"""BM25 keyword retrieval over the entity corpus."""

from __future__ import annotations

import logging
import os
import pickle
from typing import Any

logger = logging.getLogger(__name__)

_CORPUS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bm25_corpus.pkl")


class BM25Retriever:
    def __init__(self) -> None:
        self._bm25: Any = None
        self._entries: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        path = os.path.abspath(_CORPUS_PATH)
        if not os.path.exists(path):
            return
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self._bm25 = data.get("bm25")
            self._entries = data.get("entries", [])
            logger.info("BM25 corpus loaded: %d entries", len(self._entries))
        except Exception as exc:
            logger.warning("Failed to load BM25 corpus: %s", exc)

    def _save(self) -> None:
        path = os.path.abspath(_CORPUS_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"bm25": self._bm25, "entries": self._entries}, f)

    def build(self, entities: list[dict[str, Any]]) -> None:
        """Rebuild BM25 index from a list of entity dicts (name + description)."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank_bm25 not installed — BM25 disabled. pip install rank_bm25")
            return

        self._entries = [
            {
                "id": e.get("id", e.get("name", "")),
                "name": e.get("name", ""),
                "description": e.get("description", ""),
            }
            for e in entities
            if e.get("name")
        ]
        tokenized = [
            (entry["name"] + " " + entry["description"]).lower().split()
            for entry in self._entries
        ]
        if not tokenized:
            return

        self._bm25 = BM25Okapi(tokenized)
        self._save()
        logger.info("BM25 index built with %d entries", len(self._entries))

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Return top-k entities by BM25 score for *query*."""
        if self._bm25 is None or not self._entries:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25.get_scores(tokenized_query)

        indexed = sorted(
            ((float(s), i) for i, s in enumerate(scores) if s > 0),
            reverse=True,
        )
        results = []
        for score, idx in indexed[:top_k]:
            entry = dict(self._entries[idx])
            entry["bm25_score"] = score
            results.append(entry)
        return results


# Module-level singleton — loaded once on import
_retriever = BM25Retriever()


def get_bm25_retriever() -> BM25Retriever:
    return _retriever
