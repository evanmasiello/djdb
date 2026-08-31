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

## Configuration

See [.env.example](.env.example) for available settings.

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.
