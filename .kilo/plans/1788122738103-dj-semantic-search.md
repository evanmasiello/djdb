# DJ Song Semantic Search System - Implementation Plan

## Scope & Constraints
- **Single user, local-only per instance**: No auth, no cloud sync, no multi-tenancy
- **Distributable open-source desktop app**: PyWebView + FastAPI backend, packaged with PyInstaller for Win/Mac/Linux
- **Offline-first core search**: All search happens locally; no API calls at query time
- **Local Qdrant**: Docker-managed or embedded; no cloud dependency
- **System-level drag-and-drop**: Drag audio files INTO the app for ingestion; drag search results OUT to DJ software/file manager
- **Plugin integration**: Future scope; not in initial implementation

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.10+ | Best ecosystem for audio ML |
| **Desktop Shell** | PyWebView | Native OS window; supports OS drag-and-drop API; FastAPI backend on localhost |
| **Packaging** | PyInstaller | Single executable/bundle for distribution |
| **Vector DB** | Qdrant (Docker or embedded) | Best pre-filtering + hybrid search |
| **Audio Embedding** | LAION-CLAP (laion/larger_clap) | Joint audio-text space; runs locally |
| **Lyric Embedding** | BGE-M3 or text-embedding-3-small | Fast local text embeddings (optional) |
| **Query Parsing** | **Rule-based first, LLM optional** | See decision below |
| **Audio DSP** | Librosa | BPM, key, duration; offline |
| **Metadata APIs** | AudD (optional, ingestion only) | Only for untagged files; ~$0.005/recognition |
| **API Framework** | FastAPI | Serves local UI |
| **Lyrics** | WhisperX (optional, local) | GPU-accelerated transcription at ingestion |

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

## Key Design Decisions

### 1. Query Parsing: Rule-Based First
- **Phase 1**: Simple regex/string matching against known library values
  - Match exact artist names from library
  - Parse BPM ranges ("around 120", "120-130")
  - Parse musical keys (Camelot and open notation)
  - Everything else goes to semantic vector search
- **Phase 2+**: Optional LLM enhancement via OpenAI API (user-configurable)
  - More natural language understanding
  - Requires API key, internet connection
  - Can be toggled in settings

**Rationale**: Keeps core 100% offline and free. Personal library = known artists = rule-based works well.

### 2. Drag-and-Drop Strategy
- **Drag IN**: PyWebView OS file-drop → `/ingest` endpoint
- **Drag OUT**: Hybrid approach
  - Primary: OS file drag (webkit/webview2 APIs)
  - Fallback: Export buttons for M3U, Rekordbox XML, Serato SB
- **Future**: Direct DAW plugin integration (out of scope for v1)

### 3. Local-First Data Strategy
- Library stored on local filesystem
- Qdrant data stored locally (Docker volume or embedded)
- No cloud sync
- AudD as optional enrichment only for untagged files

## Implementation Phases

### Phase 1: Project Setup & Core Ingestion
1. Initialize Python project with pyproject.toml
2. Set up local Qdrant (Docker or embedded mode)
3. Implement audio file scanner + metadata extractor
4. Build optional AudD integration for unknown tracks
5. Extract CLAP embeddings for all tracks
6. Store in Qdrant with metadata payload

### Phase 2: Search Backend
1. Build Qdrant hybrid search client (pre-filter + vector)
2. Implement query parser (rule-based first, LLM optional)
3. Add optional lyrics search path
4. Result ranking + scoring

### Phase 3: Desktop App & Drag-and-Drop
1. FastAPI backend with `/search`, `/ingest`, `/library` endpoints
2. PyWebView wrapper with local HTML/JS frontend
3. Implement drag-IN for audio files
4. Implement drag-OUT for results (file drag + playlist export)
5. Simple UI: search bar, results list, library browser

### Phase 4: Polish & Distribution
1. WhisperX lyric transcription (optional)
2. Audio preview playback in UI
3. Playlist export formats (M3U, Rekordbox XML, etc.)
4. Packaging with PyInstaller for distribution
5. Documentation and installer scripts

## Drag-and-Drop Integration

### Drag In (Ingestion)
- PyWebView exposes the OS file-drop event on the window
- Frontend sends dropped file paths to `/ingest` endpoint
- Backend scans audio files, extracts metadata, generates embeddings

### Drag Out (Export to DJ Tools)
This is the critical UX feature. Options:

**Option A: OS File Drag (Recommended)**
- PyWebView supports custom drag payloads via JavaScript `DataTransfer`
- When user drags a result, the app creates a temporary file reference or m3u playlist
- OS sees it as a file drag; drops into Rekordbox, Serato, Finder, Explorer
- Limitation: PyWebView's cross-platform drag-out support is inconsistent

**Option B: Playlist Export**
- User clicks "Export to [DJ Software]" button
- Backend generates format-specific playlist (M3U, XML for Rekordbox, etc.)
- User imports into their DJ software
- More reliable, less magical, but less fluid

**Option C: Hybrid**
- Primary: OS file drag when possible
- Fallback: Export buttons for specific DJ software formats
- This covers the "just drag the results out" desire while being practical

**Recommendation: Start with Option C.** Implement basic file drag-out via PyWebView's webkit/webview2 APIs, plus an "Export Playlist" button for reliability.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CLAP embedding quality on full songs | Test 30s clip vs full track; default to first 30s + last 30s |
| Large library indexing time | Show progress in UI; run synchronously for personal use |
| WhisperX GPU requirement | Make optional; gracefully degrade to no-lyrics mode |
| PyInstaller bundle size | Use UPX compression; document requirements |
| Qdrant Docker dependency | Provide embedded fallback or SQLite-based vector store |
| PyWebView drag-out inconsistency | Implement hybrid: file drag + playlist export buttons |
| Cross-platform file path handling | Normalize paths; store relative paths or absolute with user confirmation |

## Validation Plan
1. **Unit tests**: Parser, filter builder, embedding consistency
2. **Integration test**: Ingest 10 test tracks, run hybrid queries, verify results
3. **Performance test**: 1000-track library search latency < 200ms
4. **Packaging test**: Build PyInstaller bundle on Win/Mac/Linux

## Open Questions

1. **Which DJ software should we target for playlist export?** Rekordbox, Serato, Traktor, VirtualDJ, or all of the above? This determines the export formats we need to implement.
2. **Do you have an existing music library to test with?** Needed for early validation.
3. **GPU availability?** CLAP and WhisperX run much faster on GPU; CPU fallback is possible but slow.

## Next Steps

1. Resolve DJ software targets for export
2. Begin Phase 1 implementation (project setup + ingestion)
