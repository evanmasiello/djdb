from fastapi import FastAPI, Query

from djdb.search.metadata_filter import FilterCriteria, MetadataFilter
from djdb.search.query_parser import QueryParser
from djdb.search.vector_search import VectorSearch

app = FastAPI(title="DJ DB Search API")


@app.get("/search")
def search_tracks(
    query: str = "",
    artist: str | None = None,
    bpm_min: int | None = None,
    bpm_max: int | None = None,
    key: str | None = None,
    genre: str | None = None,
    limit: int = 10,
):
    parsed = QueryParser().parse(query)
    criteria = FilterCriteria(
        artist=artist or parsed.artist,
        bpm_min=bpm_min if bpm_min is not None else (parsed.bpm_range[0] if parsed.bpm_range else None),
        bpm_max=bpm_max if bpm_max is not None else (parsed.bpm_range[1] if parsed.bpm_range else None),
        key=key or parsed.key,
        genre=genre or parsed.genre,
    )

    vector_search = VectorSearch(collection={"matches": []})
    results = vector_search.search(parsed.semantic_query or query, limit=limit)
    return {"query": query, "results": [result.__dict__ for result in results]}


@app.get("/library")
def library_tracks():
    return {"tracks": []}


@app.get("/filter-options")
def filter_options():
    return {"artists": [], "genres": [], "keys": [], "bpm": {"min": 60, "max": 180}}
