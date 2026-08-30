# DJ Song Semantic Search System - Implementation Plan

## Goal
Build a hybrid search engine for DJ music libraries that combines:
- **LLM-parsed metadata filtering** (artist, BPM, key, genre)
- **Semantic vector search** via LAION-CLAP (vibe/meaning)
- **Lyric search** via WhisperX transcription
- **Smart ingestion pipeline** with AudD/Cyanite metadata enrichment

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.10+ | Best ecosystem for audio ML (librosa, CLAP, WhisperX) |
| **Vector DB** | Qdrant (local or cloud) | Best-in-class pre-filtering + hybrid search, Python client |
| **Audio Embedding** | LAION-CLAP (laion/larger_clap) | Joint audio-text space, proven for music vibe search |
| **Lyric Embedding** | text-embedding-3-small or BGE-M3 | Fast, high-quality text embeddings for lyrics |
| **LLM Parser** | OpenAI GPT-4o-mini | Structured JSON output for query decomposition |
| **Audio DSP** | Librosa + Essentia | BPM, key, onset detection |
| **Metadata APIs** | AudD (recognition) + Soundcharts/The DJ API (features) | Cost-effective ingestion pipeline |
| **API Framework** | FastAPI | Fast, async, auto-documenting |
| **Task Queue** | Celery + Redis | Async ingestion jobs for large libraries |
| **Frontend** | TBD (web app vs desktop) | Out of scope for initial plan |

## Architecture

```
User Query: "dark brooding charli xcx track around 125 bpm"
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  LLM Query Parser (GPT-4o-mini)                     │
│  Output: {                                          │
│    metadata_filters: { artist: "Charli XCX",        │
│                        bpm_range: [120, 130] },     │
│    semantic_query: "dark brooding track"             │
│  }                                                  │
└──────────────┬──────────────────────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌──────────────┐  ┌──────────────────┐
│ Qdrant       │  │ Lyrics Index     │
│ Pre-filter:  │  │ (if lyrics       │
│ artist=Charli│  │  enabled)        │
│ XCX +        │  └──────────────────┘
│ bpm 120-130  │
│             │
│ Vector      │
│ search:     │
│ "dark       │
│ brooding"   │
└──────────────┘
       │
       ▼
  Ranked Results
```

## Data Model

### Track Payload (Qdrant)
```json
{
  "id": "uuid",
  "vector": [0.12, -0.43, ...],  // CLAP audio embedding (512-dim)
  "payload": {
    "title": "Von Dutch",
    "artist": "Charli XCX",
    "album": "BRAT",
    "genre": ["Electro-pop", "Club"],
    "bpm": 125,
    "key_camelot": "8A",
    "key_open": "G minor",
    "isrc": "USUM72401234",
    "duration_seconds": 132,
    "file_path": "/library/charli_xcx/von_dutch.mp3",
    "lyrics_snippet": "It's okay to admit...",
    "lyric_vector": [0.01, -0.88, ...],  // Optional: text embedding
    "date_added": "2026-08-30"
  }
}
```

## Implementation Phases

### Phase 1: Project Setup & Ingestion Pipeline
1. Initialize Python project with pyproject.toml
2. Set up Qdrant (Docker or cloud)
3. Implement audio file scanner + metadata extractor
4. Build AudD integration for unknown tracks
5. Extract CLAP embeddings for all tracks
6. Store in Qdrant with metadata payload

### Phase 2: Hybrid Search Backend
1. Implement LLM query parser with structured output
2. Build Qdrant hybrid search client (pre-filter + vector)
3. Implement lyrics index (separate collection or payload)
4. Add result ranking + scoring

### Phase 3: API Layer
1. FastAPI app with `/search` endpoint
2. `/ingest` endpoint for adding tracks
3. `/library` endpoint for metadata browsing

### Phase 4: Optional Enhancements
1. WhisperX lyric transcription during ingestion
2. Web UI
3. Real-time key/BPM matching (Magic Fit)
4. Audio preview playback with pitch/time-stretch

## Key Design Decisions

### 1. Metadata API Strategy
- **AudD** for recognition: ~$0.005/query, 300 free requests
- **Cache aggressively**: Only call APIs during ingestion, never at query time
- **Fallback chain**: File tags → AudD → Soundcharts

### 2. Query Parsing
- Use OpenAI structured outputs (`response_format={ "type": "json_schema" }`)
- Schema: `artist`, `bpm_range`, `key_camelot`, `genre`, `vibe_query`
- Validate against known library values to avoid hallucinations

### 3. Dual Vector Strategy
- **CLAP vector**: Captures timbre, mood, texture
- **Lyric vector**: Captures lyrical meaning
- Query routes to one or both based on user preference

### 4. Cost Control
- All API calls happen during ingestion (not search)
- Offline DSP (librosa) for BPM/key on local files
- CLAP model runs locally (no API cost)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| AudD cost at scale | Only recognize untagged files; cache ISRCs |
| CLAP embedding quality on full songs | Test both 30s clip vs full track embedding |
| LLM hallucination on metadata | Validate extracted values against library catalog |
| Large library indexing time | Parallelize with Celery; batch API calls |
| WhisperX GPU requirement | Make optional; fall back to no-lyrics mode |

## Validation Plan

1. **Unit tests**: LLM parser, filter builder, embedding consistency
2. **Integration test**: Ingest 10 test tracks, run hybrid queries, verify results
3. **Performance test**: 1000-track library search latency < 200ms
4. **Accuracy test**: Manually verify top-5 results for 20 semantic queries

## Files to Create

```
dj-semantic-search/
├── pyproject.toml
├── README.md
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── qdrant_client.py
│   │   └── schema.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   ├── metadata.py
│   │   ├── embeddings.py
│   │   └── pipeline.py
│   ├── search/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── hybrid_search.py
│   ├── lyrics/
│   │   ├── __init__.py
│   │   └── transcriber.py
│   └── api/
│       ├── __init__.py
│       ├── main.py
│       └── routes.py
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   └── test_search.py
└── docker-compose.yml
```

## Open Questions

1. **Should the frontend be web-based or desktop?** Web is more accessible; desktop enables direct DAW integration.
2. **Do you have an existing music library to test with?** Needed for early validation.
3. **GPU availability?** CLAP and WhisperX run much faster on GPU; CPU fallback is possible but slow.
