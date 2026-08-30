# DJ Semantic Search - Implementation Plan

## Goal
Build a distributable, open-source desktop app for DJs to search their local music libraries by vibe, metadata, and lyrics. Local-first, offline-capable core.

## Architecture
- **Desktop shell**: PyWebView (native window, OS drag-and-drop)
- **Backend**: FastAPI on localhost (same process)
- **Packaging**: PyInstaller for Win/Mac/Linux
- **Vector DB**: ChromaDB (pure Python, local file-based)
- **Metadata DB**: SQLite (local file, stores track metadata, lyrics, feedback, and complex filtering)
- **Audio embeddings**: LAION-CLAP (local default)
- **Lyrics**: WhisperX (optional, local)
- **Metadata**: File tags + optional AudD API for untagged files + import from DJ software (Serato, Virtual DJ, Rekordbox)

## Data Model

### ChromaDB (Vector Store)
ChromaDB stores vectors with lightweight metadata for similarity search:
- `id`: SHA-256 file hash
- `vector`: CLAP audio embedding
- `metadata`: title, artist, album, genre, bpm, key_camelot, key_open, duration_seconds, file_path, quality_flag, tags, rating, color_label, date_added
- `document`: lyrics_snippet (for keyword search)
- ChromaDB handles persistence automatically to local file

### SQLite (Metadata Store)
SQLite stores richer metadata that doesn't fit in ChromaDB's metadata fields:
- `lyrics_full`: full lyric text
- `lyrics_timestamps`: word-level timestamps from WhisperX
- `lyric_vector`: optional text embedding for semantic lyric search
- `file_hash`: SHA-256 of full file contents
- `sample_rate`, `bitrate`, `isrc`: additional audio properties
- `comments`: user notes
- `quality_notes`: detailed quality analysis text
- `feedback`: explicit ratings and implicit signals
- `import_state`: track metadata from DJ software imports

### Track ID
- Track ID = SHA-256 of full file contents. Stable across moves/renames, changes only when file content changes.

### Quality Checker
Handles lossy and lossless formats differently:
- **Lossy (MP3, M4A)**: frequency cutoff, quantization noise, entropy analysis, artifact detection
- **Lossless (FLAC, WAV, AIFF)**: clipping detection, spectral flatness, dynamic range, noise floor, stereo correlation

## What ChromaDB Is
ChromaDB is the vector database that powers the semantic search. It stores the numerical "fingerprints" (embeddings) of each track and lets you find similar tracks by meaning, not just keywords. When you search "dark brooding charli xcx", ChromaDB finds tracks whose audio vectors are mathematically close to the text vector. Metadata filtering (artist, BPM, key) is handled by SQLite for maximum flexibility. ChromaDB is pure Python with automatic file-based persistence—no binary to bundle.

## Search UX
- **Primary search bar**: Free-text for vibe/semantic queries ("dark brooding", "sunset beach vibes")
- **Empty query**: Returns all tracks (paginated), no filters applied
- **Filter chips/dropdowns**: Separate deterministic fields:
  - Artist (dropdown populated from library)
  - BPM range (slider or min/max inputs)
  - Musical key (Camelot or open notation dropdown)
  - Genre (multi-select from library tags)
- **Hybrid behavior**: Metadata filters narrow the candidate set; vector search ranks within that set

## Onboarding & Library Management
- **First-run / Empty library**: Show prominent prompt: "Drag in audio files or select a folder to get started"
- **Relocate Library**: Settings option to bulk-update file paths if music folder moves
- **File modification**: On re-scan, detect changed file hash. Update existing track record in place rather than creating duplicate.

## API Keys & External Services
- **AudD**: API key stored in Settings UI. Only used during ingestion for untagged files.
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
1. `pyproject.toml` with deps: fastapi, chromadb, laion-clap, librosa, pywebview, pyinstaller
   2. ChromaDB setup (file-based persistence)
3. SQLite setup (local file for track metadata, lyrics, feedback)
4. Audio file scanner (recursive folder scan, format validation)
5. Metadata extractor (file tags via mutagen)
6. Metadata import from DJ software (Serato SB, Virtual DJ XML, Rekordbox XML)
7. Embedding provider abstraction: Local CLAP encoder (default)
8. Ingestion pipeline: scan → metadata → embed → store
9. Optional AudD integration for missing metadata

### Phase 2: Search Backend
1. ChromaDB search client (vector similarity)
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
3. Export formats: Rekordbox XML, Serato SB, M3U (stream to disk for large exports)
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
When a model is added, the app runs background pre-computation but does NOT claim to automatically score retrieval quality. General audio-text benchmarks don't measure DJ-specific retrieval, and two models with the same dimensions can have completely different "meaning spaces."

**What we're testing:** retrieval quality on actual DJ queries against the user's library, not vector dimensions.

**Background Pre-computation:**
1. Generate a standardized query set from the user's library:
   - 20-50 vibe queries sampled from common DJ vocabulary
   - 10 hybrid metadata+vibe queries (artist + BPM + key + vibe)
   - Queries generated from actual library metadata
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

### Per-Model Collections
To support model comparison and avoid full re-ingestion on every switch:
- Each model gets its own ChromaDB collection (e.g., `tracks_clap_v1`, `tracks_mert_v1`)
- SQLite stores model-independent data (track metadata, lyrics, feedback)
- When user switches models, app simply queries a different ChromaDB collection
- When user compares models side-by-side, both collections are queried in parallel
- If user deletes a model, its collection is dropped

### Per-Model Default Settings
Store tuned defaults per model in registry:
- `similarity_threshold`: CLAP ~0.7, MERT ~0.65
- `result_limit`: Some models need more results to surface variety
- `filter_strength`: Weight of metadata pre-filtering vs. vector similarity

These are starting points, not optimized values. Real optimization comes from side-by-side comparisons and implicit feedback.

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
   - Semantic search: ChromaDB cosine similarity on `lyric_vector`
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
Detect potential upsampling, transcoding artifacts, and low-quality source material. DJs care because upsampled files (e.g., 128kbps MP3 labeled as 320kbps) sound worse on quality sound systems. A trash recording converted to WAV is still a trash recording.

### Detection Method
Analyze spectral content differently based on format:

**Lossy formats (MP3, M4A/AAC):**
1. **Frequency cutoff analysis**: Genuine 320kbps MP3 has content up to ~20kHz; upsampled 128kbps usually cuts off around 16kHz
2. **Quantization noise**: Check for abnormal noise floors in high frequencies
3. **Entropy analysis**: Compare actual spectral entropy to expected entropy for claimed bitrate
4. **Artifact detection**: Look for pre-echo, ringing, or other encoding artifacts

**Lossless formats (FLAC, WAV, AIFF):**
1. **Clipping detection**: Sample-level clipping indicates poor source or bad rip
2. **Spectral flatness**: Extremely flat spectrum can indicate synthesized/generated audio
3. **Dynamic range**: Abnormally compressed dynamic range may indicate loudness normalization abuse
4. **Noise floor**: High noise floor relative to signal indicates poor source (tape hiss, vinyl noise, bad recording)
5. **Stereo correlation**: Abnormally low correlation can indicate phase issues or poor mastering

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
- **Model switching**: Switch ChromaDB collection; no re-ingestion needed
- **Cloud backend**: Not in v1. Stretch goal: managed cloud worker with per-user API keys
- **DJ software import**: Serato, Virtual DJ, Rekordbox metadata import supported
- **Vector DB**: ChromaDB (pure Python, file-based persistence)

## Assumptions & Gaps to Address

### Settings Storage
- **Assumption**: Settings are stored in a JSON file in the app's data directory
- **Gap**: Need to define exact location per OS (XDG on Linux, AppData on Windows, ~/Library/Application Support on macOS)
- **Decision**: Use platformdirs library for cross-platform paths; settings.json in that directory

### FastAPI Lifecycle in PyWebView
- **Assumption**: FastAPI server runs in the same process as PyWebView
- **Gap**: How is the server started/stopped? Thread? Subprocess?
- **Decision**: FastAPI runs in a background thread within the PyWebView process; app startup starts the server, shutdown stops it cleanly

### ChromaDB Persistence
- **Assumption**: ChromaDB's file-based persistence works reliably across app restarts
- **Gap**: ChromaDB stores data in a local directory; need to ensure it's in the app data directory, not a temp folder
- **Decision**: Use platformdirs for ChromaDB data directory. ChromaDB handles persistence automatically; no separate binary or process management needed.

### Audio Format Support
- **Assumption**: All audio files are valid and readable
- **Gap**: Corrupted files, DRM, unsupported codecs
- **Decision**: Support MP3, FLAC, WAV, AIFF, M4A (AAC). Skip unsupported/corrupt files with error logging. Show skipped files in UI.

### Library Path Handling
- **Assumption**: File paths are stable
- **Gap**: User moves music folder, uses external drive, or has different mount points
- **Decision**: Store absolute paths in SQLite metadata. Provide "Relocate Library" feature in settings to bulk-update paths. Detect missing files on startup.

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
- **Track ID**: SHA-256 of full file contents. Stable across moves and renames, changes only when file content changes.
- **Path + mtime**: Used for change detection, not ID generation. If file hash matches but path changed, update path in place.

### Cross-Platform Paths
- **Assumption**: Paths work across OS
- **Gap**: Windows paths (`C:\Users\...`) won't work on macOS/Linux and vice versa
- **Decision**: Store absolute paths in SQLite. ChromaDB collections are not shared across OS. If user moves library, use "Relocate Library" feature.

## Software Architecture

### Process Model
```
┌─────────────────────────────────────────────────────────────────┐
│  Desktop App (User's Machine)                                  │
│  ┌──────────────┐  ┌────────────────────┐  ┌───────────────┐  │
│  │ PyWebView    │  │ FastAPI (thread)   │  │ ChromaDB      │  │
│  │ (UI thread)  │  │ localhost:8000     │  │ (pure Python) │  │
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
│     │ WhisperX     │ │ AudD API │ │ SQLite   │              │
│     │ (opt, local) │ │ (opt)    │ │ (metadata│              │
│     │              │ │          │ │  + lyrics)│              │
│     └──────────────┘ └──────────┘ └──────────┘              │
└─────────────────────────────────────────────────────────────────┘
```
- **Main thread**: PyWebView UI
- **Background thread**: FastAPI server (localhost only)
- **Vector DB**: ChromaDB (pure Python, file-based persistence, no binary)
- **Metadata DB**: SQLite file for track metadata, lyrics, timestamps, feedback, and complex filtering
- **Optional process**: WhisperX (GPU)
- **No remote worker in v1**: Out of scope, see stretch goals

### Module Structure
```
src/
├── __init__.py
├── config.py          # Settings, paths, environment
├── main.py            # App entry point, PyWebView + FastAPI lifecycle
├── models.py          # Pydantic models for API and payloads
├── db/
│   ├── __init__.py
│   ├── chroma.py      # ChromaDB client, collection management
│   ├── sqlite.py      # SQLite schema, metadata, lyrics, feedback
│   └── schema.py      # Data models and validation
├── ingestion/
│   ├── __init__.py
│   ├── scanner.py     # Recursive folder scan, format validation
│   ├── metadata.py    # mutagen tags, AudD API client, DJ software import
│   ├── embeddings.py  # Local CLAP encoder (default)
│   ├── quality.py     # Audio quality checker (upsampling detection)
│   └── pipeline.py    # Orchestrator: scan → metadata → embed → store
├── search/
│   ├── __init__.py
│   ├── parser.py      # Rule-based query parser
│   ├── lyrics.py      # Lyric search (keyword + semantic)
│   └── hybrid.py      # ChromaDB search + SQLite metadata filtering
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
- **Vector data**: ChromaDB collections (one per model, file-based persistence)
- **Metadata DB**: SQLite file for track metadata, lyrics, timestamps, feedback, and import state
- **Ingestion state**: Tracked via file hash in SQLite; resume on restart
- **Model cache**: Hugging Face cache in platformdirs models directory

### Error Handling
- **ChromaDB unavailable**: Retry with backoff; if persistent, show error in UI and disable search
- **Corrupt audio file**: Log error, skip file, show in UI skipped-files list
- **Ingestion interrupted**: Partial results preserved; resume on next scan via SQLite state
- **File modified**: On re-scan, detect changed file hash. Update existing track record rather than creating duplicate.

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
1. User enables "Compare Mode" in Settings
2. Selects two models: current (A) and candidate (B)
3. For each search, results from both models are queried from their respective ChromaDB collections and shown side-by-side
4. User rates each model's results independently (1-10)
5. App computes comparative metrics: "Model B wins on 8/12 queries, avg +1.2 rating"
6. User can switch to winning model with one click (no re-ingestion needed)

### Per-Model Default Settings
Store tuned defaults per model in registry:
```json
{
  "model_id": "laion/larger_clap",
  "dimensions": 512,
  "chroma_collection": "tracks_clap_v1",
  "default_similarity_threshold": 0.7,
  "default_result_limit": 20,
  "default_filter_strength": 0.8,
  "score": 7.8,
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

### Auto-Scan / File Watcher (Stretch Goal)
- Background watcher detects new files in indexed folders and ingests them automatically
- Requires platform-specific file watcher (inotify/FSEvents/ReadDirectoryChangesW)
- Debounce logic to avoid re-ingesting during bulk file operations
- Not included in initial release; manual re-scan button is the v1 alternative

### Model Fine-Tuning (Stretch Goal)
- Collect feedback data in structured form for potential future fine-tuning
- Requires: aggregated data from many users, GPU infrastructure, ML engineering
- Not feasible from single-user feedback alone
- v1 scope: use feedback for model selection and ranking parameters only

## Open Questions
1. **Test library available?** Needed for early validation.
