# DJ Song Semantic Search System - Implementation Plan

## Scope & Constraints
- **Single user, local-only**: No auth, no cloud sync, no multi-tenancy
- **Cross-platform desktop app** via PyWebView + FastAPI backend, packaged with PyInstaller
- **Offline-first core search**: All search happens locally; no API calls at query time
- **Local Qdrant**: Embedded or Docker-managed; no cloud Qdrant needed
- **No LLM dependency for core search**: (Decision pending - see below)

## Tech Stack (Revised for Local/Personal Use)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.10+ | Best ecosystem for audio ML |
| **Desktop Shell** | PyWebView | Native OS window rendering local HTML/JS frontend; FastAPI backend runs on localhost in same process |
| **Packaging** | PyInstaller | Single executable/bundle for Win/Mac/Linux |
| **Vector DB** | Qdrant (local/Docker) | Best pre-filtering + hybrid search; can run embedded |
| **Audio Embedding** | LAION-CLAP (laion/larger_clap) | Joint audio-text space; runs locally, no API cost |
| **Lyric Embedding** | BGE-M3 or text-embedding-3-small | Fast local text embeddings (if lyrics enabled) |
| **LLM Parser** | **TBD - see question below** | Optional enhancement |
| **Audio DSP** | Librosa | BPM, key, duration; offline, no API |
| **Metadata APIs** | AudD (optional, ingestion only) | Only for untagged files; ~$0.005/recognition |
| **API Framework** | FastAPI | Serves both local UI and potential future integrations |
| **Task Queue** | Not needed | Personal library = synchronous ingestion acceptable |
| **Lyrics** | WhisperX (optional, local) | GPU-accelerated transcription at ingestion time |

## Architecture (Revised for Local Use)

```
┌──────────────────────────────────────────────────────────┐
│  Desktop App Window (PyWebView)                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Local HTML/JS Frontend                            │  │
│  │  - Search bar                                      │  │
│  │  - Library browser                                 │  │
│  │  - Ingestion progress                              │  │
│  └───────────────────────┬────────────────────────────┘  │
└──────────────────────────┼───────────────────────────────┘
                           │ HTTP (localhost)
┌──────────────────────────▼───────────────────────────────┐
│  FastAPI Backend (same process)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Ingestion   │  │ Search       │  │ Library        │  │
│  │ Pipeline    │  │ Engine       │  │ Browser        │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
│                           │                              │
│          ┌────────────────┼────────────────┐            │
│          ▼                ▼                ▼            │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│   │ Qdrant       │ │ WhisperX     │ │ AudD API     │   │
│   │ (local)      │ │ (optional)   │ │ (optional)   │   │
│   └──────────────┘ └──────────────┘ └──────────────┘   │
└──────────────────────────────────────────────────────────┘
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
    "lyric_vector": [0.01, -0.88, ...],  // Optional
    "date_added": "2026-08-30"
  }
}
```

## Implementation Phases

### Phase 1: Project Setup & Ingestion Pipeline
1. Initialize Python project with pyproject.toml
2. Set up local Qdrant (Docker or embedded mode)
3. Implement audio file scanner + metadata extractor
4. Build optional AudD integration for unknown tracks
5. Extract CLAP embeddings for all tracks
6. Store in Qdrant with metadata payload

### Phase 2: Search Backend
1. Build Qdrant hybrid search client (pre-filter + vector)
2. Implement query parser (TBD: LLM vs rule-based)
3. Add optional lyrics search path
4. Result ranking + scoring

### Phase 3: Desktop App Shell
1. FastAPI backend with `/search`, `/ingest`, `/library` endpoints
2. PyWebView wrapper opening local frontend
3. Simple HTML/JS UI for search and library browsing

### Phase 4: Polish
1. WhisperX lyric transcription (optional)
2. Audio preview playback in UI
3. Packaging with PyInstaller for distribution

## Key Design Decisions

### 1. Local-First Data Strategy
- **Library stored on local filesystem**: DJ points app at their music folder
- **Qdrant data stored locally**: Either Docker volume or embedded binary
- **No cloud sync**: All processing happens on the user's machine
- **AudD as optional enrichment**: Only for untagged files; one-time cost per track

### 2. Query Parsing Strategy
**Critical decision pending - see question below.**

### 3. Cost Control
- Zero recurring API costs for core functionality
- CLAP and WhisperX run locally (no inference API)
- Optional AudD calls only during ingestion of untagged files

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CLAP embedding quality on full songs | Test 30s clip vs full track; default to first 30s + last 30s |
| Large library indexing time | Show progress in UI; run synchronously for personal use |
| WhisperX GPU requirement | Make optional; gracefully degrade to no-lyrics mode |
| PyInstaller bundle size | Use UPX compression; document requirements |
| Qdrant Docker dependency | Provide embedded fallback or SQLite-based vector store |

## Validation Plan
1. **Unit tests**: Parser, filter builder, embedding consistency
2. **Integration test**: Ingest 10 test tracks, run hybrid queries, verify results
3. **Performance test**: 1000-track library search latency < 200ms
4. **Packaging test**: Build PyInstaller bundle on Win/Mac/Linux

## Open Questions

1. **Should the frontend be web-based or desktop?** Web is more accessible; desktop enables direct DAW integration.
2. **Do you have an existing music library to test with?** Needed for early validation.
3. **GPU availability?** CLAP and WhisperX run much faster on GPU; CPU fallback is possible but slow.

## Remaining Critical Decision

**Query Parsing: LLM vs Rule-Based?**

For a local, personal tool, the query parser can be either:

**Option A: Rule-Based (Recommended)**
- Regex/string matching against known library values (artists, genres, keys in your library)
- Parse patterns like "artist X", "BPM range", "key"
- Zero cost, zero latency, works offline
- Limitation: Less flexible for vague queries ("something dark")

**Option B: LLM-Based (OpenAI API)**
- GPT-4o-mini structured outputs
- More natural language understanding
- Requires API key, internet, adds ~100-300ms latency per search
- Better for complex/ambiguous queries

**Recommendation: Start with rule-based.** For a personal library, you know your artists and can match against them directly. Add LLM as an optional enhancement later if needed. This keeps the tool fully offline and free.

**Question: Are you comfortable with rule-based parsing for metadata extraction, or do you want the flexibility of an LLM from day one?**
