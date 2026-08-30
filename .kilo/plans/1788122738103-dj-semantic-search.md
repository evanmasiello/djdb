# DJ Semantic Search - Implementation Plan

## Goal
Build a distributable, open-source desktop app for DJs to search their local music libraries by vibe, metadata, and lyrics. Local-first, offline-capable core.

## Architecture
- **Desktop shell**: PyWebView (native window, OS drag-and-drop)
- **Backend**: FastAPI on localhost (same process)
- **Packaging**: PyInstaller for Win/Mac/Linux
- **Vector DB**: Qdrant (Docker or embedded)
- **Audio embeddings**: LAION-CLAP (local, offline)
- **Lyrics**: WhisperX (optional, local)
- **Metadata**: File tags + optional AudD API for untagged files

## Data Model
Each track in Qdrant:
```json
{
  "id": "uuid",
  "vector": [...],  // CLAP audio embedding
  "payload": {
    "title": "...",
    "artist": "...",
    "album": "...",
    "genre": ["..."],
    "bpm": 125,
    "key_camelot": "8A",
    "key_open": "G minor",
    "isrc": "...",
    "duration_seconds": 132,
    "file_path": "/path/to/track.mp3",
    "lyrics_snippet": "...",
    "lyric_vector": [...],  // optional
    "date_added": "2026-08-30"
  }
}
```

## Implementation Phases

### Phase 1: Project Setup & Ingestion
1. `pyproject.toml` with deps: fastapi, qdrant-client, laion-clap, librosa, pywebview, pyinstaller
2. Qdrant setup (Docker compose + embedded fallback)
3. Audio file scanner (recursive folder scan, format validation)
4. Metadata extractor (file tags via mutagen)
5. CLAP embedding extraction
6. Ingestion pipeline: scan → metadata → embed → store
7. Optional AudD integration for missing metadata

### Phase 2: Search Backend
1. Qdrant hybrid search client (pre-filter + vector similarity)
2. Rule-based query parser:
   - Match known artists from library
   - Parse BPM ranges ("around 120", "120-130")
   - Parse keys (Camelot: 1A-12A/1B-12B, open: C minor, F major)
   - Remaining text → semantic vector query
3. Result ranking and scoring
4. Optional lyrics search path

### Phase 3: Desktop App
1. FastAPI endpoints: `/search`, `/ingest`, `/library`, `/export`
2. PyWebView wrapper
3. HTML/JS frontend:
   - Search bar with results list
   - Library browser
   - Ingestion progress UI
4. Drag-IN: file drop → `/ingest`
 5. Drag-OUT: hybrid approach
    - OS file drag from results (webkit/webview2)
    - Fallback: export buttons (M3U, Rekordbox XML, Serato SB)

### Phase 4: Polish & Distribution
1. WhisperX lyric transcription (optional, GPU-aware)
2. Audio preview playback in UI
3. Export formats: Rekordbox XML, Serato SB, M3U
4. PyInstaller packaging
5. README and setup docs

## Key Decisions
- **Query parsing**: Rule-based v1, LLM optional v2 (keeps core offline/free)
- **Drag-out**: Hybrid file drag + export buttons
- **Export formats**: Rekordbox XML, Serato SB, M3U
- **Metadata**: Offline-first; AudD only for untagged files during ingestion
- **Open source**: Yes, for trust and community

## Open Questions
1. **Test library available?** Needed for early validation.
