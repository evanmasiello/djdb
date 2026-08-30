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
- **Metadata**: File tags + optional AudD API for untagged files + import from DJ software (Serato, Virtual DJ, Rekordbox)

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
5. Metadata import from DJ software (Serato SB, Virtual DJ XML, Rekordbox XML)
6. Embedding provider abstraction:
    - Local CLAP encoder (default)
    - Remote API client (optional, for large libraries / no GPU)
7. Ingestion pipeline: scan → metadata → embed → store
8. Optional AudD integration for missing metadata

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

## Metadata Import from DJ Software

Allow users to import existing metadata from their DJ software libraries to bootstrap the app's database.

### Supported Formats
- **Rekordbox**: XML export (`export.xml` or `master.db`)
- **Serato**: SB database file (`_Serato_` folder structure)
- **Virtual DJ**: XML database file (`database.xml`)

### Imported Fields
- Title, artist, album, genre, BPM, key, duration, file path, date added
- User-defined tags/labels (Serato cue points, VDJ tags, Rekordbox color codes)
- Play count and history (optional, for library analytics)

### UI Flow
1. User clicks "Import Library" in Settings
2. Select source DJ software and file/folder
3. App parses file, shows preview of matched tracks
4. User confirms import; tracks merged with existing library (dedup by file path)
5. Missing metadata (e.g., key, BPM) can be computed locally during import

### Conflict Resolution
- If a track already exists in the app (matched by file path), update metadata from import
- If file path has changed (e.g., after relocate library), match by file hash
- Preserve app-specific fields (comments, rating, color_label) during merge

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

### Per-Model Evaluation
When a model is added, the app evaluates it on the user's library before allowing it to be used for search. General audio-text benchmarks don't measure DJ-specific retrieval quality, and two models with the same dimensions can have completely different "meaning spaces."

**What we're testing:** retrieval quality on actual DJ queries, not just vector dimensions. Whether the model's representation of music meaning aligns with how DJs think about tracks.

**Evaluation Protocol:**
1. On model addition, run a standardized test suite against the user's library:
   - 20-50 vibe queries ("dark", "uplifting", "summer vibes")
   - 10 artist+BPM+key hybrid queries
   - 10 lyric semantic queries (if lyrics enabled)
2. For each query, compute Precision@5 and user rating (1-10) if in test mode
3. Store model score in registry and display in Settings UI

**Model-Specific Default Settings:**
Different models may need different search parameters:
- Similarity threshold: CLAP might need 0.7, MERT might need 0.65
- Filter weights: Some models respond better to stricter metadata pre-filtering
- Result count: Some models produce tighter clusters and need more results

Store per-model defaults in registry alongside score.

### Model Leaderboard
In Settings UI, show ranked list of available models based on:
1. Evaluation score on user's library (primary)
2. Model size (smaller = faster on CPU)
3. Dimensions (affects Qdrant memory usage)
4. User ratings from test mode

Allow user to compare models side-by-side before switching.

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
- **Embedding**: Local CLAP default only for v1
- **Model switching**: Full re-embedding with explicit user confirmation
- **Cloud backend**: Not in v1. Stretch goal: managed cloud worker with per-user API keys
- **DJ software import**: Serato, Virtual DJ, Rekordbox metadata import supported

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
- `POST /import` - Import metadata from DJ software (Serato, VDJ, Rekordbox)
- `GET /settings` - Current settings
- `POST /settings` - Update settings

### AI-Generated Music Detection
Flag tracks that may be AI-generated based on spectral and structural artifacts.
- Analyze high-frequency rolloff, transient sharpness, spectral entropy consistency, and stereo phase correlation
- Output: `ai_detection_flag` (`likely_human`, `suspected_ai`, `inconclusive`) + confidence score
- Caveat: Not 100% reliable; false positives on poorly mastered human music. Flag as "suspected" only.
- UI: Optional filter to hide/show suspected AI tracks

## Testing & Evaluation

### What We Can and Cannot Evaluate Automatically
- **Cannot**: Automatically judge if "dark brooding" matches the user's intent. No ground truth exists without user feedback.
- **Cannot**: Compute true Precision@5/Recall@5 without labeled relevance data.
- **Cannot**: Translate your test library ratings to other users' libraries. DJ vocabularies and library distributions are personal.
- **Can**: Verify deterministic filters work (artist, BPM, key constraints).
- **Can**: Detect regressions by comparing same-query results across model versions.
- **Can**: Track implicit user behavior (clicks, previews, exports) as relevance signals.

### Model Evaluation Protocol
When a user adds a new model, the app evaluates it in the background without blocking the UI.

**Background Pre-computation:**
1. Generate a standardized query set from the user's library:
   - 20-50 vibe queries sampled from common DJ vocabulary
   - 10 hybrid metadata+vibe queries (artist + BPM + key + vibe)
   - Queries generated from actual library metadata (existing artists, genres, BPMs)
2. Run each query through the new model
3. Store results for each query (track IDs + ranks)
4. Do NOT compute a score yet — there is no ground truth
5. Show in Settings UI: "Model X — evaluating in background"

**Scoring (requires user feedback):**
- Precision@5, Coverage, and other metrics are only computed after the user provides relevance signals
- Sources of relevance:
  - **Explicit**: Test mode ratings (1-10 slider after searches)
  - **Implicit**: Clicks, preview plays, exports/drags to DJ software, query refinements
- Once ≥20 rated queries accumulate, compute composite score and display: "Rated 7.8/10 on your library"
- Until then, show "Not enough data — use test mode to rate results"

### Side-by-Side Model Comparison
Encourage the user to compare models directly when switching:

**Workflow:**
1. User enables "Compare Mode" in Settings
2. Selects two models: current (A) and candidate (B)
3. For each search, results from both models are shown side-by-side
4. User rates each model's results independently (1-10)
5. App computes comparative metrics: "Model B wins on 8/12 queries, avg +1.2 rating"
6. User can switch to winning model with one click

**Why this matters:**
- Vector ranking is the entire search "intelligence" — there are few other knobs to turn
- If we're just ranking non-filtered songs by cosine similarity, the model IS the ranking function
- Side-by-side comparison is the only reliable way to choose between models
- Your ratings on your library are personal and don't generalize, but they tell you which model works for YOUR use case

### Per-Model Default Settings
Store tuned defaults per model in registry:
- `similarity_threshold`: CLAP ~0.7, MERT ~0.65 (tighter vs looser clusters)
- `result_limit`: Some models need more results to surface variety
- `filter_strength`: Weight of metadata pre-filtering vs. vector similarity

These are starting points, not optimized values. Real optimization comes from your side-by-side comparisons and implicit feedback.

### Implicit Feedback Signals
Collect lightweight interaction data to continuously refine search quality:

**Track per-query:**
- Query text and parsed filters
- Results shown (IDs + ranks)
- User clicked result → implicit relevance
- User played preview → stronger relevance signal
- User exported/dragged to DJ software → strongest relevance signal
- User refined query within 30 seconds → previous results were unhelpful
- User cleared search without clicking → no relevant results

**Do NOT store:**
- PII or identifiable info
- Exact timestamps (only relative time)
- Audio content or full file paths in feedback logs (use track IDs only)

**Use implicit data to:**
- Boost models that produce more clicks/exports in side-by-side tests
- Identify queries with zero engagement → flag for review
- Adjust ranking weights per model based on actual user behavior

### Explicit Test Mode (For You)
In Settings, enable "Test Mode" for detailed manual evaluation:
- After each search, show 1-10 slider: "How well do these results match?"
- Optional text: "What's missing or wrong?"
- Stores structured feedback with query + results + rating
- Use this to compare models side-by-side or tune parameters

**Your test data is valuable for:**
- Finding bugs in filter logic or ranking
- Identifying systematic failures (e.g., "CLAP fails at low-BPM jazz")
- Calibrating implicit feedback weights
- Building a personal benchmark suite

**Your test data does NOT directly translate to other users** because:
- Different libraries have different genre/artist distributions
- "Dark brooding" means something different to a techno DJ vs. a hip-hop DJ
- Model performance is library-dependent

### Model Comparison Workflow
1. User adds Model B while Model A is active
2. App evaluates Model B in background against test suite
3. When complete, Settings shows: "Model B rated 8.2/10 vs current Model A at 7.8/10"
4. User can switch with one click; app warns about re-embedding time
5. After switching, implicit feedback starts tracking Model B's real-world performance

### Per-Model Default Settings
Store tuned defaults per model in registry:
```json
{
  "model_id": "laion/larger_clap",
  "dimensions": 512,
  "default_similarity_threshold": 0.7,
  "default_result_limit": 20,
  "default_filter_strength": 0.8,
  "score": 7.8,
  "precision@5": 0.65,
  "coverage": 0.9,
  "last_evaluated": "2026-08-30"
}
```

These defaults are applied automatically when the user selects the model.

## Stretch Goals

### Managed Cloud Backend
For users who want offloaded embedding without self-hosting infrastructure:
- You operate a managed worker service (FastAPI app on GPU infrastructure)
- Users sign up through the app and receive a per-user API key
- App calls your cloud endpoint for embedding generation
- You handle deployment, scaling, and billing
- User experience: toggle "Cloud Mode" in Settings, enter API key, done
- Requires: cloud hosting, user accounts, billing integration, usage tracking
- Out of scope for v1; revisit after core app is stable

### Self-Hosted Remote Worker (Out of Scope for v1)
- Desktop app can offload embeddings to a remote worker
- Worker is a standalone FastAPI service deployable anywhere (local GPU, cloud, etc.)
- Backend-agnostic REST API: multipart upload → JSON vector response
- User provides worker URL + optional API key in Settings
- Not included in initial release to keep scope manageable

## Open Questions
1. **Test library available?** Needed for early validation.
