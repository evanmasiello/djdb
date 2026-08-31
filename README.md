# DJ Semantic Search

A distributable, open-source desktop app for DJs to search their local music libraries by vibe, metadata, and lyrics. Local-first, offline-capable core.

## What It Does

- **Semantic vibe search**: Type "dark brooding techno" or "sunset festival vibes" and find matching tracks using AI audio embeddings (LAION-CLAP)
- **Metadata filtering**: Narrow results by artist, BPM, musical key, and genre
- **Lyric search**: Find tracks by specific lyrics or lyrical themes (powered by WhisperX transcription)
- **DJ software integration**: Import existing metadata from Rekordbox, Serato, and Virtual DJ. Drag search results directly into your DJ software with full metadata intact
- **Model registry**: Switch between different audio-text embedding models and compare results side-by-side
- **Audio quality checker**: Detect upsampling, transcoding artifacts, and low-quality source material
- **Open source**: Fully local, no cloud required, no telemetry

## Architecture

- **Desktop shell**: PyWebView (native window, OS drag-and-drop)
- **Backend**: FastAPI on localhost (same process)
- **Vector DB**: ChromaDB (pure Python, file-based persistence)
- **Metadata DB**: SQLite (track metadata, lyrics, feedback, complex filtering)
- **Audio embeddings**: LAION-CLAP (local default)
- **Lyrics**: WhisperX (optional, local)

## Getting Started

### Prerequisites

- Python 3.10+
- pip or poetry
- (Optional) NVIDIA GPU for faster embedding generation and WhisperX transcription

### Installation

```bash
git clone https://github.com/yourusername/dj-semantic-search.git
cd dj-semantic-search
pip install -r requirements.txt
```

### Running the App

```bash
python -m src.main
```

### Packaging for Distribution

```bash
pyinstaller src/main.py --onefile --windowed
```

## Usage

1. **First run**: Drag audio files into the app, or select a folder to scan
2. **Import existing library**: Use Settings to import metadata from Rekordbox, Serato, or Virtual DJ
3. **Search**: Type a vibe description ("dark", "uplifting", "summer vibes") and use filters for artist, BPM, key
4. **Drag to DJ software**: Drag search results directly into Rekordbox, Serato, Traktor, etc. Full metadata travels with the track

## Project Structure

```
src/
├── config.py          # Settings, paths, environment
├── main.py            # App entry point, PyWebView + FastAPI lifecycle
├── models.py          # Pydantic models for API and payloads
├── db/
│   ├── chroma.py      # ChromaDB client, collection management
│   ├── sqlite.py      # SQLite schema, metadata, lyrics, feedback
│   └── schema.py      # Data models and validation
├── ingestion/
│   ├── scanner.py     # Recursive folder scan, format validation
│   ├── metadata.py    # mutagen tags, AudD API client, DJ software import
│   ├── embeddings.py  # Local CLAP encoder (default)
│   ├── quality.py     # Audio quality checker
│   └── pipeline.py    # Orchestrator: scan → metadata → embed → store
├── search/
│   ├── parser.py      # Rule-based query parser
│   ├── lyrics.py      # Lyric search (keyword + semantic)
│   └── hybrid.py      # ChromaDB search + SQLite metadata filtering
├── export/
│   ├── dragout.py     # Drag-out handler with full track metadata
│   ├── rekordbox.py   # Rekordbox XML export
│   ├── serato.py      # Serato SB export
│   └── m3u.py         # M3U export
├── lyrics/
│   └── transcriber.py # WhisperX wrapper
└── api/
    ├── routes.py      # FastAPI route definitions
    └── schemas.py     # Request/response models
```

## Development Timeline

See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for detailed phases.

### MVP (8-12 weeks)
- Project setup + ingestion
- Search backend (ChromaDB + SQLite)
- Desktop app shell (PyWebView)
- DJ software metadata import
- Drag-out with full metadata
- Basic packaging

### Add-ons
- Lyrics & model registry (3-4 weeks)
- Audio quality checker + preview playback (2-3 weeks)
- Enhanced export formats (2-3 weeks)

### Stretch Goals
- Managed cloud backend for remote embedding
- Auto-scan / file watcher
- Smart mode LLM for query parsing
- Model fine-tuning from aggregated feedback
- AI-generated music detection

## Tech Stack

| Component | Choice |
|-----------|--------|
| Desktop | PyWebView |
| Backend | FastAPI |
| Vector DB | ChromaDB |
| Metadata | SQLite |
| Audio Embeddings | LAION-CLAP |
| Lyrics | WhisperX |
| Packaging | PyInstaller |

## Contributing

This is an open-source project. Contributions are welcome. Please open an issue or PR.

## License

MIT
