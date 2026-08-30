# DJ Semantic Search - Implementation Plan

## Goal
Build a distributable, open-source desktop app for DJs to search their local music libraries by vibe, metadata, and lyrics. Local-first, offline-capable core.

## Architecture
- **Desktop shell**: PyWebView (native window, OS drag-and-drop)
- **Backend**: FastAPI on localhost (same process)
- **Packaging**: PyInstaller for Win/Mac/Linux
- **Vector DB**: Qdrant (bundled portable binary, no Docker)
- **Audio embeddings**: LAION-CLAP (local default; optional remote worker for large libraries/no GPU)
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
    "file_hash": "sha256...",
    "sample_rate": 44100,
    "bitrate": 320,
    "lyrics_snippet": "...",
    "lyrics_full": "...",
    "lyrics_timestamps": [...],
    "lyric_vector": [...],  // optional
    "tags": ["warmup", "peak", "vinyl-only"],
    "rating": 4,
    "color_label": "green",
    "comments": "User notes...",
    "date_added": "2026-08-30"
  }
}
```

## What Qdrant Is
Qdrant is the vector database that powers the semantic search. It stores the numerical "fingerprints" (embeddings) of each track and lets you find similar tracks by meaning, not just keywords. When you search "dark brooding charli xcx", Qdrant finds tracks whose audio vectors are mathematically close to the text vector, optionally filtered by metadata. It runs as a bundled binary inside the app—no Docker, no cloud.

## Search UX
- **Primary search bar**: Free-text for vibe/semantic queries ("dark brooding", "sunset beach vibes")
- **Filter chips/dropdowns**: Separate deterministic fields:
  - Artist (dropdown populated from library)
  - BPM range (slider or min/max inputs)
  - Musical key (Camelot or open notation dropdown)
  - Genre (multi-select from library tags)
- **Hybrid behavior**: Metadata filters narrow the candidate set; vector search ranks within that set

## Onboarding & Library Management
- **First-run**: Prompt user to add music folders before searching
- **Auto-scan**: Background watcher detects new files in indexed folders and ingests them automatically
- **Relocate Library**: Settings option to bulk-update file paths if music folder moves

## API Keys & External Services
- **AudD**: API key stored in Settings UI. Only used during ingestion for untagged files.
- **Remote Worker**: URL + optional API key stored in Settings UI.
- **LLM API** (optional): API key for remote query routing (OpenAI, Anthropic, etc.). Stored in Settings UI. Only used if Smart Mode is enabled and remote API is selected. Opt-in with privacy disclosure.

## WhisperX & Model Selection
- **First enable**: Prompt user to download WhisperX model. Show size and estimated time.
- **Model choice**: Offer smaller/faster models (e.g., `tiny`, `base`) vs larger/more accurate (`medium`, `large`). User picks based on GPU/RAM.
- **Smart Mode for query parsing**: Two options:
  - **Local LLM**: Small downloadable models (Phi-3 Mini 3.8B, Llama 3.2 1B/3B). Requires model download (~2-8GB).
  - **Remote LLM API**: External API (OpenAI, Anthropic, etc.). Requires API key in Settings. Query text sent externally; opt-in with disclosure.
  - Default to rule-based for offline reliability.

## Implementation Phases

### Phase 1: Project Setup & Ingestion
1. `pyproject.toml` with deps: fastapi, qdrant-client, laion-clap, librosa, pywebview, pyinstaller
 2. Qdrant setup (bundled portable binary)
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

For users with large libraries or no GPU, the desktop app can offload CLAP embedding generation to a remote worker. The worker is a separate deployable service that speaks a simple HTTP API. Any cloud backend (AWS Lambda, GCP Cloud Run, Azure Functions, Fly.io, etc.) can host it. The protocol is backend-agnostic: standard REST with multipart uploads and JSON responses.

### Why This Exists
CLAP embedding on CPU is slow (seconds per track). GPU is fast but not everyone has one. A remote worker lets users:
- Use a GPU server on their local network
- Rent a GPU instance in the cloud for bulk ingestion
- Share one worker across multiple desktop app instances

### Worker Architecture
The worker is a standalone FastAPI app (same codebase, different entrypoint). It does not need Qdrant, PyWebView, or any desktop-only dependencies. It only needs:
- FastAPI + Uvicorn
- CLAP encoder (local or remote)
- Standard Python HTTP libraries

Deployment options:
- **Local network**: `python -m app worker --host 0.0.0.0 --port 8000` on a GPU machine
- **Cloud**: Docker container deployed to any container host
- **Serverless**: Packaged as a Lambda/Cloud Function (note: cold starts may be slow for large batches)

### Worker API Contract

#### Health Check
```
GET /health
Response: { "status": "ok", "model": "laion/larger_clap", "dimensions": 512 }
```

#### Embed Single Audio File
```
POST /v1/embed-audio
Headers:
  Authorization: Bearer <optional_api_key>
  Content-Type: multipart/form-data
Body:
  file: <audio file>
  model: <optional model override>
Response 200:
{
  "vector": [0.12, -0.43, ...],  // 512-dim float array
  "duration": 132.5,
  "model": "laion/larger_clap",
  "sample_rate": 44100
}
Response 4xx/5xx:
{
  "error": "unsupported_format",
  "message": "File codec not supported"
}
```

#### Embed Batch (for throughput)
```
POST /v1/embed-audio/batch
Headers:
  Authorization: Bearer <optional_api_key>
  Content-Type: multipart/form-data
Body:
  files: [<audio1>, <audio2>, ...]
  model: <optional model override>
Response 200:
{
  "results": [
    { "vector": [...], "duration": 132.5, "file_hash": "sha256..." },
    { "error": "corrupt_file", "message": "..." }
  ]
}
```

### Client Integration (Desktop App)

Settings UI: "Remote Embedding" section:
- Worker URL input (e.g., `http://192.168.1.50:8000`)
- API key input (optional, for auth)
- Test connection button (calls `/health`)
- Enable/disable toggle
- Fallback behavior dropdown: "Use local CPU" / "Pause ingestion" / "Skip failed files"

Request flow:
1. Desktop app has a queue of unembedded tracks
2. If worker is enabled: send files to worker `/v1/embed-audio/batch`
3. If worker responds: store vectors in Qdrant, mark track as embedded
4. If worker fails: fallback per settings (local CPU, pause, or skip)
5. Never re-upload files that already have a cached vector

### Security & Privacy

- Audio files contain copyrighted material. Remote worker is fully opt-in.
- Auth: Bearer token or API key. Worker can reject requests without valid credentials.
- Transport: User is responsible for TLS. For local networks, HTTP is acceptable; for cloud, HTTPS is strongly recommended.
- Worker logs: By default, worker does not log file contents. It may log metadata (file hash, duration, model used) for debugging.
- No telemetry: Worker does not phone home to any central service.

### Example Deployments

**Local GPU machine:**
```bash
# On GPU machine
python -m app worker --host 0.0.0.0 --port 8000
# Desktop app points to http://192.168.1.50:8000
```

**Docker on local network:**
```bash
docker run -p 8000:8000 \
  -e WORKER_API_KEY=secret \
  -v /app/models:/app/models \
  dj-semantic-search/worker:latest
```

**Cloud Run / Fly.io:**
```bash
# Deploy worker as container
# Set WORKER_API_KEY env var
# Expose port 8000
# Desktop app points to https://worker.example.com
```

### Failure Modes

| Scenario | Behavior |
|----------|----------|
| Worker URL unreachable | Fallback to local CPU (if enabled) or pause ingestion with warning |
| Worker returns 401 | Show auth error in UI; prompt user to check API key |
| Worker returns 413 (file too large) | Skip file, log error, continue with next |
| Worker returns 500 | Retry once with backoff; if still failing, fallback or pause |
| Network timeout | Retry with exponential backoff; max 3 retries per file |
| Model mismatch | Worker returns supported models in `/health`; client validates before sending |

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

**Decision: Full Re-embedding.** On model switch, show confirmation modal with estimated time. User confirms, app clears collection and re-ingests. Prevents silent data corruption and keeps implementation simple.

## Query Parsing: Smart Mode vs Rule-Based

### Rule-Based (Default)
- Parse known values from the user's own library:
  - Exact artist name matches
  - BPM range patterns ("around 120", "120-130", "130+")
  - Key patterns (Camelot 1A-12A/1B-12B, open notation "C minor")
  - Genre tags
- Provide autocomplete/suggestions as the user types, populated from actual library data
- Remaining text → semantic vector query

### Smart Mode (Optional)
- Single text field for natural language queries
- Two implementation options:
  - **Local LLM**: Small downloadable model (Phi-3 Mini 3.8B, Llama 3.2 1B/3B). Requires settings toggle + model download (~2-8GB). Zero latency, zero cost, fully offline.
  - **Remote LLM API**: Call external API (OpenAI, Anthropic, etc.) for query decomposition. Requires settings toggle + API key. Lower local resource usage, requires internet. Privacy consideration: query text sent to external service.
- Extracts: artist, bpm_range, key_camelot, genre, vibe_query, lyric_mode
- Falls back to rule-based if model/API unavailable or disabled

### Query Routing & Decomposition

### Query Types
1. **Metadata filter**: artist, BPM, key, genre
2. **Audio vibe query**: semantic search against CLAP embeddings ("dark brooding", "sunset vibes")
3. **Lyric keyword**: exact/fuzzy phrase match in lyrics ("I saw a waterfall")
4. **Lyric semantic**: thematic search against lyric embeddings ("songs about waterfalls")

### Default: Rule-Based Router
- No LLM required. Runs locally, zero latency, zero cost.
- Steps:
  1. Match known artists/genres/keys from library → metadata filters
  2. Detect BPM range patterns → metadata filter
  3. Detect quoted phrases or short specific text → lyric keyword search
  4. Remaining text → audio vibe query
  5. If lyrics enabled and query looks conceptual → also run lyric semantic search
- Always search audio vectors. Lyrics are additive.

### Optional: Smart Mode
- Two implementation options:
  - **Local LLM**: Small downloadable model (Phi-3 Mini 3.8B, Llama 3.2 1B/3B). Requires settings toggle + model download.
  - **Remote LLM API**: External API (OpenAI, Anthropic, etc.). Requires settings toggle + API key. Query text sent externally; opt-in with disclosure.
- Single text field → structured JSON: `{artist, bpm_range, key_camelot, genre, vibe_query, lyric_mode}`
- Falls back to rule-based if unavailable or disabled

### Recommended Approach
**Rule-based first, always search audio vectors.** An LLM is overkill for routing and adds weight/dependency. For a DJ tool, exact artist/BPM/key matching via dropdowns + autocomplete is more reliable than parsing free text. The "smart mode" single-field experience can be layered on later as an optional enhancement for users who prefer it.

## Lyric Search Strategy

### Two Search Modes
1. **Keyword match**: Exact or fuzzy text search within lyrics
   - "I walk a lonely road" → matches exact phrase
   - "lonely road" → fuzzy match, returns tracks containing those words
   - Best for: DJs who remember specific lines

2. **Semantic lyric search**: Embed full lyrics and search by meaning
   - "songs about waterfalls" → matches songs whose lyrics are about water, nature, flowing, etc.
   - "songs with sad lyrics" → matches melancholic themes even without the word "sad"
   - Best for: Theme/emotion-based discovery ("find me something with hopeful lyrics")

### Lyric Query Router
For lyric searches specifically, the router decides keyword vs semantic based on query characteristics:
- **Keyword mode** (default): 
  - Quoted phrases: `"lonely road"`
  - Short, specific text: 1-4 words that look like a phrase
  - Contains proper nouns or unusual words
- **Semantic mode**:
  - Conceptual phrases: "songs about waterfalls", "songs with hopeful lyrics"
  - Abstract themes: "heartbreak", "summer love", "growing up"
  - Longer queries with abstract nouns
- **Both** (UI toggle):
  - Runs keyword first, then semantic, merges results
  - Removes duplicates, ranks by combined score

### Implementation
- Store `lyrics_full` (plain text transcript) and `lyrics_timestamps` (word-level timestamps from WhisperX)
- Generate `lyric_vector` using a text embedding model (BGE-M3 or similar)
- When user enables lyric search:
  - Route based on query characteristics above
  - Keyword search: SQLite FTS5 or simple text search over `lyrics_full`
  - Semantic search: Qdrant cosine similarity on `lyric_vector`
- UI toggle: "Search lyrics" checkbox + mode selector (Both / Keyword / Semantic)
- **Default mode: Both**. Runs keyword and semantic in parallel, merges results.
- When keyword match is used: highlight matched words/phrases in `lyrics_snippet` with `<mark>` tags for frontend display

### Use Case for Semantic Lyric Search
- DJ wants "songs with uplifting/vibe lyrics" for a feel-good set
- DJ searches "songs about summer love" and gets tracks thematically related even if exact words differ
- Cross-lingual: if embedding model supports it, "songs about love" matches love songs in Spanish, French, etc.

### Recommendation
Provide both. Keyword for precision, semantic for theme discovery. Default to keyword for exact phrases, semantic for vague/thematic queries.

## Audio Quality Checker

### Purpose
Detect potential upsampling and estimate true bitrate/quality. DJs care because upsampled files (e.g., 128kbps MP3 labeled as 320kbps) sound worse on quality sound systems.

### Detection Method
Analyze spectral content and encoding artifacts:
1. **Frequency cutoff analysis**: Genuine 320kbps MP3 has content up to ~20kHz; upsampled 128kbps usually cuts off around 16kHz
2. **Quantization noise**: Check for abnormal noise floors in high frequencies
3. **Entropy analysis**: Compare actual spectral entropy to expected entropy for claimed bitrate
4. **Artifact detection**: Look for pre-echo, ringing, or other encoding artifacts

### Output
Store in payload:
```json
{
  "estimated_true_bitrate": 192,
  "quality_flag": "possibly_upsampled",  // "verified" | "possibly_upsampled" | "low_quality"
  "quality_notes": "Frequency cutoff at 16.2kHz suggests 192-224kbps source"
}
```

### UI Display
- Show quality flag in library browser with color indicator
- Allow filtering by quality (e.g., "show only verified high-quality files")
- Export quality flag in playlist metadata

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

### Qdrant Packaging
- **Assumption**: Qdrant runs locally without external dependencies
- **Gap**: Qdrant requires a Rust binary; not a pure Python library
- **Decision**: Bundle Qdrant's portable binary with the PyInstaller app (~20MB compressed). Ship platform-specific binaries for Win/Mac/Linux. No Docker required. Binary lives in app's data directory and is launched/stopped by the app.

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
- **Track ID**: SHA-256 of (absolute file path + file size + last modified timestamp). Stable across app restarts, changes if file is modified.
- **File hash**: SHA-256 of full file contents, stored in payload for deduplication and integrity checks.

### Cross-Platform Paths in Qdrant
- **Assumption**: Paths work across OS
- **Gap**: Windows paths (C:\Users\...) won't work on macOS/Linux and vice versa
- **Decision**: Store absolute paths. Qdrant collection is not shared across OS. If user moves library, use "Relocate Library" feature.

## Software Architecture

### Process Model
```
┌─────────────────────────────────────────────────────────────────┐
│  Desktop App (User's Machine)                                  │
│  ┌──────────────┐  ┌────────────────────┐  ┌───────────────┐  │
│  │ PyWebView    │  │ FastAPI (thread)   │  │ Qdrant       │  │
│  │ (UI thread)  │  │ localhost:8000     │  │ (child proc) │  │
│  └──────────────┘  └─────────┬──────────┘  └───────────────┘  │
│                              │                                 │
│                    ┌─────────┴──────────┐                     │
│                    │  Business Logic    │                     │
│                    │  - Ingestion       │                     │
│                    │  - Search          │                     │
│                    │  - Export          │                     │
│                    └─────────┬──────────┘                     │
│                              │                                │
│              ┌───────────────┼───────────┐                    │
│              ▼               ▼           ▼                    │
│     ┌──────────────┐ ┌──────────┐ ┌──────────┐              │
│     │ WhisperX     │ │ AudD API │ │ Remote   │              │
│     │ (opt, local) │ │ (opt)    │ │ Worker   │◄─────────────┤
│     └──────────────┘ └──────────┘ └──────────┘   HTTP        │
│                                                   (network)   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Remote Worker (Any Machine / Cloud)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ FastAPI Worker                                        │  │
│  │  - CLAP encoder (GPU or CPU)                          │  │
│  │  - Model registry (pluggable embeddings)              │  │
│  │  - Auth (Bearer token / API key)                      │  │
│  │  - Batch processing                                   │  │
│  │  - No Qdrant, no UI, no PyWebView                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```
- **Desktop app**: PyWebView UI + FastAPI backend + Qdrant + optional local processes
- **Remote worker**: Standalone FastAPI service, deployable anywhere. Speaks standard HTTP. No desktop dependencies.
- **Communication**: Desktop app sends multipart audio to worker over HTTP/HTTPS. Worker returns JSON vectors.

### Module Structure
```
src/
├── __init__.py
├── config.py          # Settings, paths, environment
├── main.py            # App entry point, PyWebView + FastAPI lifecycle
├── models.py          # Pydantic models for API and payloads
├── db/
│   ├── __init__.py
│   ├── qdrant.py      # Qdrant client, collection management
│   └── schema.py      # Payload definitions, indexes
├── ingestion/
│   ├── __init__.py
│   ├── scanner.py     # File system watcher, recursive scan
│   ├── metadata.py    # mutagen tags, AudD API client
│   ├── embeddings.py  # CLAP encoder abstraction (local/remote)
│   ├── quality.py     # Audio quality checker (upsampling detection)
│   └── pipeline.py    # Orchestrator: scan → metadata → embed → store
├── search/
│   ├── __init__.py
│   ├── parser.py      # Rule-based query parser
│   ├── lyrics.py      # Lyric search (keyword + semantic)
│   └── hybrid.py      # Qdrant search with metadata filters
├── export/
│   ├── __init__.py
│   ├── rekordbox.py   # XML export
│   ├── serato.py      # SB export
│   └── m3u.py         # M3U export
├── lyrics/
│   ├── __init__.py
│   └── transcriber.py # WhisperX wrapper
└── api/
    ├── __init__.py
    ├── routes.py      # FastAPI route definitions
    └── schemas.py     # Request/response models
```

### State Management
- **Settings**: `settings.json` in platformdirs data directory
- **Track data**: Qdrant collection with payloads
- **Ingestion state**: Tracked in Qdrant via `date_added` and file hash; no separate state store
- **Model cache**: Hugging Face cache in platformdirs models directory

### Error Handling
- **Qdrant unavailable**: Retry with backoff; if persistent, show error in UI and disable search
- **Remote worker unreachable**: Fall back to local embedding; show warning in ingestion progress
- **Corrupt audio file**: Log error, skip file, show in UI skipped-files list
- **Ingestion interrupted**: Partial results preserved; resume on next scan

### Logging
- File-based logging to app data directory (`logs/app.log`)
- Log levels: INFO for normal operation, WARNING for skipped files, ERROR for failures
- No telemetry or external logging

### API Contracts (High-Level)
- `POST /ingest` - Accept file paths or folder paths; returns job ID
- `GET /ingest/status/{job_id}` - Progress, status, errors
- `POST /search` - Query with optional filters; returns ranked results
- `GET /library` - Paginated track list with optional filters
- `POST /export` - Export selected tracks to format; returns download URL
- `GET /settings` - Current settings
- `POST /settings` - Update settings
- `POST /worker/embed` - (Worker mode only) Accept audio, return vector

### AI-Generated Music Detection
Flag tracks that may be AI-generated based on spectral and structural artifacts.
- Analyze high-frequency rolloff, transient sharpness, spectral entropy consistency, and stereo phase correlation
- Output: `ai_detection_flag` (`likely_human`, `suspected_ai`, `inconclusive`) + confidence score
- Caveat: Not 100% reliable; false positives on poorly mastered human music. Flag as "suspected" only.
- UI: Optional filter to hide/show suspected AI tracks

## Open Questions
1. **Test library available?** Needed for early validation.
