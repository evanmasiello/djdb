"""Audio file scanning and detection."""

import hashlib
import logging
from pathlib import Path
from typing import Iterator, Optional, Tuple
from dataclasses import dataclass

from djdb.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AudioFile:
    """Detected audio file with metadata."""
    path: Path
    file_hash: str
    file_size: int
    codec: str


class AudioScanner:
    """Recursively scan directories for audio files and generate file hashes."""

    def __init__(self, supported_formats: Optional[Tuple[str, ...]] = None):
        """
        Initialize scanner.
        
        Args:
            supported_formats: Tuple of file extensions to scan for.
                              Defaults to settings.supported_audio_formats.
        """
        self.supported_formats = supported_formats or settings.supported_audio_formats
        self.logger = logging.getLogger(__name__)

    def scan_directory(self, directory: Path, recursive: bool = True) -> Iterator[AudioFile]:
        """
        Scan directory for audio files.
        
        Args:
            directory: Path to directory to scan
            recursive: If True, scan subdirectories recursively
            
        Yields:
            AudioFile objects for each audio file found
        """
        if not directory.exists():
            self.logger.warning(f"Directory not found: {directory}")
            return

        if not directory.is_dir():
            self.logger.warning(f"Path is not a directory: {directory}")
            return

        self.logger.info(f"Scanning directory: {directory}")

        pattern = "**/*" if recursive else "*"
        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue

            if file_path.suffix.lstrip(".").lower() not in self.supported_formats:
                continue

            try:
                audio_file = self._process_file(file_path)
                if audio_file:
                    yield audio_file
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
                continue

    def _process_file(self, file_path: Path) -> Optional[AudioFile]:
        """
        Process single audio file and compute hash.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            AudioFile object with file hash, or None if error
        """
        try:
            file_size = file_path.stat().st_size
            file_hash = self._compute_file_hash(file_path)
            codec = file_path.suffix.lstrip(".").lower()

            self.logger.debug(f"Found audio file: {file_path} (hash: {file_hash[:16]}...)")

            return AudioFile(
                path=file_path,
                file_hash=file_hash,
                file_size=file_size,
                codec=codec,
            )
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            return None

    @staticmethod
    def _compute_file_hash(file_path: Path, chunk_size: int = 65536) -> str:
        """
        Compute SHA-256 hash of file contents.
        
        Args:
            file_path: Path to file
            chunk_size: Size of chunks to read (default 64KB)
            
        Returns:
            SHA-256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash {file_path}: {e}")
            raise

    def scan_files(self, file_paths: list[Path]) -> Iterator[AudioFile]:
        """
        Scan specific files.
        
        Args:
            file_paths: List of file paths to scan
            
        Yields:
            AudioFile objects for valid audio files
        """
        for file_path in file_paths:
            if not file_path.is_file():
                self.logger.warning(f"File not found: {file_path}")
                continue

            try:
                audio_file = self._process_file(file_path)
                if audio_file:
                    yield audio_file
            except Exception as e:
                self.logger.error(f"Error scanning {file_path}: {e}")
                continue
