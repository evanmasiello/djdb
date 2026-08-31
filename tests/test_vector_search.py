import numpy as np

from djdb.search.vector_search import VectorSearch, SearchResult


def test_vector_search_returns_ranked_matches_and_handles_empty_terms():
    searcher = VectorSearch()

    class FakeResult:
        def __init__(self, id, distance):
            self.id = id
            self.distance = distance

    searcher._query_embedding = lambda *args, **kwargs: np.array([1.0, 0.0, 0.0], dtype=float)
    searcher._collection = {
        "matches": [
            FakeResult("track-1", 0.15),
            FakeResult("track-2", 0.40),
            FakeResult("track-3", 0.90),
        ]
    }

    results = searcher.search("dark house", limit=2)

    assert len(results) == 2
    assert results[0].track_id == "track-1"
    assert results[0].score >= results[1].score
    assert results[0].metadata == {}

    empty_results = searcher.search("   ", limit=5)
    assert empty_results == []
