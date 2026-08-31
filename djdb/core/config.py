"""Application configuration and settings."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    # App
    app_name: str = "DJ DB"
    app_version: str = "0.1.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = "INFO"

    # Paths
    app_data_dir: Path = Path.home() / ".djdb"
    library_dir: Optional[Path] = None
    db_path: Path = app_data_dir / "djdb.db"
    chromadb_path: Path = app_data_dir / "chromadb"
    models_cache_dir: Path = app_data_dir / "models"

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_reload: bool = debug

    # Audio Processing
    chunk_size: int = 4096
    audio_sample_rate: int = 16000

    # Embeddings
    default_embedding_model: str = "laion/larger_clap"
    embedding_dimension: int = 512

    # Search
    default_top_k: int = 50
    max_top_k: int = 1000

    # File Formats
    supported_audio_formats: tuple = ("mp3", "flac", "wav", "m4a", "aiff", "ogg", "opus")

    # External APIs (optional)
    audd_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **data):
        super().__init__(**data)
        # Create app data directories if they don't exist
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.chromadb_path.mkdir(parents=True, exist_ok=True)
        self.models_cache_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
