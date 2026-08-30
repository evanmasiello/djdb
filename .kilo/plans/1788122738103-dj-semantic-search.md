# DJ Semantic Search - Implementation Plan

## Goal
Build a distributable, open-source desktop app for DJs to search their local music libraries by vibe, metadata, and lyrics. Local-first, offline-capable core.

## Architecture
- **Desktop shell**: PyWebView (native window, OS drag-and-drop)
- **Backend**: FastAPI on localhost (same process)
- **Packaging**: PyInstaller for Win/Mac/Linux
- **Vector DB**: Qdrant (Docker or embedded)
- **Audio embeddings**: LAION-CLAP (local default; optional remote API for large libraries)
- **Remote embedding API**: Optional cloud endpoint to offload CLAP generation for users without GPUs or with large libraries
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
5. Embedding provider abstraction:
   - Local CLAP encoder (default)
   - Remote API client (optional, for large libraries / no GPU)
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

## Remote Embedding Worker (Optional)
For users with large libraries or no GPU, provide an optional remote embedding service. Same codebase, separate process, configured entirely through the app settings UI.

### Worker Mode
- Same FastAPI repo exposes an additional `/v1/embed-audio` endpoint when run in "worker" mode
- User launches worker on a GPU machine via simple script (`python -m app worker` or Docker)
- Desktop app Settings UI has a "Remote Embedding" section:
  - Worker URL input (e.g., `http://192.168.1.50:8000`)
  - API key input (optional, for auth)
  - Test connection button
  - Enable/disable toggle

### API Contract
- **Endpoint**: `POST /v1/embed-audio`
- **Input**: Multipart audio file or URL
- **Output**: CLAP vector (512-dim float array) + duration
- **Batching**: Support multiple files per request for throughput
- **Auth**: Bearer token or API key (optional for self-hosted)

### Client Integration
- Desktop app checks settings for remote worker URL
- If configured: sends embedding jobs to worker, falls back to local if unreachable
- If not configured: uses local CLAP encoder (CPU or GPU)
- Cache results locally; never re-upload same file
- Ingestion progress UI shows whether embeddings are local or remote

### Privacy Considerations
- Audio files contain copyrighted material
- Remote worker is opt-in via Settings UI with clear disclosure
- Self-hosted worker keeps data on user's network
- No telemetry or logging of audio content by default

## Model Registry (Pluggable Embeddings)
Allow users to switch audio-text embedding models via Hugging Face Hub or local paths, without rebuilding the app.

### Supported Model Formats
- Hugging Face Hub model IDs (e.g., `laion/larger_clap`, `microsoft/BEATs`)
- Local model paths (for custom fine-tunes)
- Curated preset list in Settings UI: LAION-CLAP, MERT, BEATs, etc.

### Model Requirements
For a model to be pluggable, it must:
- Accept raw audio waveform + text as inputs
- Output a fixed-dimension embedding vector
- Be loadable via `transformers` or `clap` libraries
- Have consistent input/output contracts

### Settings UI: "Embedding Model" Section
- Dropdown of preset models with dimensions and description
- "Add custom model" button (HF Hub ID or local path)
- Model info display: name, dimensions, size, last validated
- Test button: embed a sample audio snippet to verify compatibility
- Active model stored in local settings

### Critical: Model Switching Behavior
When a user switches models, existing vectors in Qdrant are incompatible because:
- Different models produce different vector dimensions
- Even same dimensions have different geometric spaces
- Old vectors cannot be compared to new query vectors

**Options for handling model switches:**
A) **Require full re-embedding**: Clear collection, re-process entire library with new model. User is warned and must confirm.
B) **Versioned collections**: Create new Qdrant collection per model version (e.g., `tracks_clap_v1`, `tracks_mert_v1`). Switch is instant but uses more disk.
C) **Lazy migration**: Re-embed tracks on-demand during search if vector dimension mismatches. Slow first search, then fast.

**Recommendation: Option A (Full Re-embedding).** On model switch, show confirmation modal with estimated time. User confirms, app clears collection and re-ingests. Prevents silent data corruption and keeps implementation simple.

## Key Decisions
- **Query parsing**: Rule-based v1, LLM optional v2 (keeps core offline/free)
- **Drag-out**: Hybrid file drag + export buttons
- **Export formats**: Rekordbox XML, Serato SB, M3U
- **Metadata**: Offline-first; AudD only for untagged files during ingestion
- **Open source**: Yes, for trust and community
- **Embedding**: Local CLAP default; optional remote worker for large libraries / no GPU
- **Remote worker**: Same repo, configured via Settings UI (no CLI flags)
- **Model switching**: Full re-embedding with explicit user confirmation

## Assumptions & Gaps to Address

### Settings Storage
- **Assumption**: Settings are stored in a JSON file in the app's data directory
- **Gap**: Need to define exact location per OS (XDG on Linux, AppData on Windows, ~/Library/Application Support on macOS)
- **Decision**: Use platformdirs library for cross-platform paths; settings.json in that directory

### FastAPI Lifecycle in PyWebView
- **Assumption**: FastAPI server runs in the same process as PyWebView
- **Gap**: How is the server started/stopped? Thread? Subprocess?
- **Decision**: FastAPI runs in a background thread within the PyWebView process; app startup starts the server, shutdown stops it cleanly

### Qdrant Embedded Mode
- **Assumption**: "Docker or embedded" implies both are equally viable
- **Gap**: Qdrant's embedded mode is actually a Rust binary that needs to be packaged
- **Decision**: Default to Docker for dev; for packaged app, use Qdrant's embedded binary or ship a portable Qdrant binary. Provide clear Docker alternative for power users.

### Audio Format Support
- **Assumption**: All audio files are valid and readable
- **Gap**: Corrupted files, DRM, unsupported codecs
- **Decision**: Support MP3, FLAC, WAV, AIFF, M4A (AAC). Skip unsupported/corrupt files with error logging. Show skipped files in UI.

### Library Path Handling
- **Assumption**: File paths are stable
- **Gap**: User moves music folder, uses external drive, or has different mount points
- **Decision**: Store absolute paths in Qdrant payload. Provide "Relocate Library" feature in settings to bulk-update paths. Detect missing files on startup.

### PyInstaller Data Files
- **Assumption**: Static assets (HTML/JS frontend) are available
- **Gap**: PyInstaller doesn't include non-Python files by default
- **Decision**: Use `--add-data` for frontend assets. Models downloaded at runtime to user's data directory, not bundled.

### Model Cache Location
- **Assumption**: HF models are cached somewhere
- **Gap**: Transformers cache location varies by OS and environment
- **Decision**: Use platformdirs for model cache location. Allow user to override in settings. Download on first use, not at install time.

### Settings UI Implementation
- **Assumption**: Settings UI is HTML/JS within PyWebView
- **Gap**: Native OS settings vs web UI
- **Decision**: Settings are a web page within PyWebView. Persisted to local JSON. No native settings dialogs.

### Ingestion Cancellation
- **Assumption**: Ingestion runs to completion
- **Gap**: User may want to stop a long job
- **Decision**: Background thread with cancellation token. UI shows progress and cancel button. Partial results are preserved.

### Duplicate Detection
- **Assumption**: Each file is unique
- **Gap**: User drops same file twice, or has duplicates in library
- **Decision**: Deduplicate by file path hash (SHA-256 of absolute path + modification time). Skip if already indexed. Allow manual re-ingestion.

### Track ID Strategy
- **Assumption**: UUID is stable across sessions
- **Gap**: What if file moves or is re-ingested?
- **Decision**: Track ID = SHA-256 of (absolute file path + file size + last modified timestamp). Stable across app restarts, changes if file is modified.

### Cross-Platform Paths in Qdrant
- **Assumption**: Paths work across OS
- **Gap**: Windows paths (C:\Users\...) won't work on macOS/Linux and vice versa
- **Decision**: Store absolute paths. Qdrant collection is not shared across OS. If user moves library, use "Relocate Library" feature.

## Open Questions
1. **Test library available?** Needed for early validation.
