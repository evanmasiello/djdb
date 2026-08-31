# DJ DB - Semantic Search for DJ Music Libraries

A distributable, open-source desktop app for DJs to search their local music libraries by vibe, metadata, and lyrics. Local-first, offline-capable core with support for importing metadata from major DJ software (Rekordbox, Serato, Virtual DJ).

## Features

### MVP (Core)
- **Semantic Search**: Search by vibe/mood ("dark brooding", "sunset beach vibes") using LAION-CLAP embeddings
- **Metadata Filters**: Filter by artist, BPM range, musical key, genre
- **DJ Software Import**: Bootstrap your library by importing from Rekordbox, Serato, or Virtual DJ
- **Drag & Drop**: Drag audio files to ingest, drag results to DJ software with full metadata intact
- **Local-First**: Works entirely offline, no cloud required
- **Vector DB**: ChromaDB for fast similarity search with SQLite for rich metadata

### Planned Add-ons
- Lyric transcription and semantic lyric search
- Multiple embedding model support
- Audio quality analysis
- Lyrics with timestamps (WhisperX)
- Platform-specific packaging

## Installation

### Prerequisites
- Python 3.9+
- pip or poetry

### Setup

```bash
# Clone the repo
git clone https://github.com/evanmasiello/djdb.git
cd djdb

# Install dependencies
pip install -e ".[dev]"

# Create .env file (optional)
cp .env.example .env
```

## Architecture

- **Frontend**: HTML/JS in PyWebView (native desktop window)
- **Backend**: FastAPI on localhost
- **Vector DB**: ChromaDB (pure Python, local file-based)
- **Metadata DB**: SQLite (full track metadata, lyrics, quality metrics)
- **Audio Embeddings**: LAION-CLAP (default), pluggable via Hugging Face Hub
- **Lyrics**: Optional WhisperX for local transcription

## Development

### Run Tests
```bash
pytest tests/
```

### Lint & Format
```bash
black djdb tests
ruff check djdb tests
```

### Type Check
```bash
mypy djdb
```

## Project Structure

```
djdb/
├── core/           # Configuration, logging, database
├── ingestion/      # Audio scanning, metadata extraction, embeddings
├── search/         # Vector & metadata search
├── api/            # FastAPI routes
├── ui/             # Desktop UI (HTML/JS)
├── models/         # Data models & embeddings
└── tests/          # Test suite
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

## Configuration

See [.env.example](.env.example) for available settings.

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.
