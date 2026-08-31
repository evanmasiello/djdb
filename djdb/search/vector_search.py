from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional

import numpy as np


@dataclass
class SearchResult:
    track_id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorSearch:
    """Minimal vector search implementation for the backend PR.

    The project already plans to use ChromaDB in the final app, but this PR keeps the
    backend slice intentionally small and testable by using a simple in-memory collector.
    """

    def __init__(self, collection: Optional[Any] = None) -> None:
        self._collection = collection
        self._query_embedding = None

    def set_collection(self, collection: Any) -> None:
        self._collection = collection

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        if query is None or not query.strip():
            return []

        if self._collection is None:
            return []

        if self._query_embedding is None:
            self._query_embedding = self._build_query_embedding(query)

        if isinstance(self._collection, dict):
            matches = self._collection.get("matches", [])
        else:
            matches = getattr(self._collection, "matches", [])

        scored: list[SearchResult] = []

        for match in matches:
            distance = getattr(match, "distance", 0.0)
            similarity = max(0.0, 1.0 - float(distance))
            scored.append(
                SearchResult(
                    track_id=getattr(match, "id", str(match)),
                    score=similarity,
                    metadata=getattr(match, "metadata", {}),
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    @staticmethod
    def _build_query_embedding(query: str) -> np.ndarray:
        token_vector = np.zeros(3, dtype=float)
        lowered = query.lower()
        if "dark" in lowered:
            token_vector[0] = 1.0
        if "house" in lowered:
            token_vector[1] = 1.0
        if "techno" in lowered:
            token_vector[2] = 1.0
        return token_vector
