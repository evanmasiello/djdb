from fastapi.testclient import TestClient

from djdb.api.search_api import app


client = TestClient(app)


def test_search_endpoint_returns_ranked_results():
    response = client.get(
        "/search",
        params={"query": "dark brooding house", "artist": "Daft Punk", "bpm_min": 120, "bpm_max": 126, "key": "8A", "genre": "house"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert isinstance(payload["results"], list)


def test_library_endpoint_returns_tracks():
    response = client.get("/library")
    assert response.status_code == 200
    payload = response.json()
    assert "tracks" in payload
    assert isinstance(payload["tracks"], list)


def test_filter_options_endpoint_returns_lists():
    response = client.get("/filter-options")
    assert response.status_code == 200
    payload = response.json()
    assert "artists" in payload
    assert "genres" in payload
