"""Audio metadata extraction from file tags."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from mutagen.aiff import AIFF

logger = logging.getLogger(__name__)


@dataclass
class TrackMetadata:
    """Extracted track metadata from audio file tags."""
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    bpm: Optional[int] = None
    key_camelot: Optional[str] = None
    key_open: Optional[str] = None
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    bitrate: Optional[int] = None
    channels: Optional[int] = None
    codec: Optional[str] = None
    isrc: Optional[str] = None
    comments: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class MetadataExtractor:
    """Extract metadata from audio files using mutagen."""

    def __init__(self):
        """Initialize metadata extractor."""
        self.logger = logging.getLogger(__name__)

    def extract(self, file_path: Path) -> TrackMetadata:
        """
        Extract metadata from audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            TrackMetadata object with extracted fields
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        codec = file_path.suffix.lstrip(".").lower()

        try:
            if codec == "mp3":
                metadata = self._extract_id3(file_path)
            elif codec == "flac":
                metadata = self._extract_flac(file_path)
            elif codec in ("ogg", "oga"):
                metadata = self._extract_vorbis(file_path)
            elif codec == "opus":
                metadata = self._extract_opus(file_path)
            elif codec in ("m4a", "mp4"):
                metadata = self._extract_mp4(file_path)
            elif codec in ("wav", "wave"):
                metadata = self._extract_wave(file_path)
            elif codec in ("aiff", "aif"):
                metadata = self._extract_aiff(file_path)
            else:
                self.logger.warning(f"Unsupported format: {codec}")
                metadata = TrackMetadata(codec=codec)

            # Ensure codec is set
            if not metadata.codec:
                metadata.codec = codec

            # Get audio properties
            info_metadata = self._extract_audio_info(file_path)
            if info_metadata:
                for key, value in asdict(info_metadata).items():
                    if value is not None and not getattr(metadata, key):
                        setattr(metadata, key, value)

            return metadata

        except Exception as e:
            self.logger.error(f"Error extracting metadata from {file_path}: {e}")
            return TrackMetadata(codec=codec)

    def _extract_id3(self, file_path: Path) -> TrackMetadata:
        """Extract ID3v2 metadata from MP3."""
        try:
            audio = EasyID3(file_path)
        except Exception:
            # Fallback if ID3v2 not found
            audio = {}

        return TrackMetadata(
            title=self._get_first(audio.get("title")),
            artist=self._get_first(audio.get("artist")),
            album=self._get_first(audio.get("album")),
            genre=self._get_first(audio.get("genre")),
            bpm=self._parse_int(self._get_first(audio.get("bpm"))),
            isrc=self._get_first(audio.get("isrc")),
            key_camelot=self._get_first(audio.get("initialkey")),
        )

    def _extract_flac(self, file_path: Path) -> TrackMetadata:
        """Extract FLAC metadata."""
        try:
            audio = FLAC(file_path)
        except Exception:
            return TrackMetadata()

        return TrackMetadata(
            title=self._get_first(audio.get("title")),
            artist=self._get_first(audio.get("artist")),
            album=self._get_first(audio.get("album")),
            genre=self._get_first(audio.get("genre")),
            bpm=self._parse_int(self._get_first(audio.get("bpm"))),
            isrc=self._get_first(audio.get("isrc")),
            key_camelot=self._get_first(audio.get("initialkey")),
        )

    def _extract_vorbis(self, file_path: Path) -> TrackMetadata:
        """Extract Vorbis comment metadata (OGG Vorbis)."""
        try:
            audio = OggVorbis(file_path)
        except Exception:
            return TrackMetadata()

        return TrackMetadata(
            title=self._get_first(audio.get("title")),
            artist=self._get_first(audio.get("artist")),
            album=self._get_first(audio.get("album")),
            genre=self._get_first(audio.get("genre")),
            bpm=self._parse_int(self._get_first(audio.get("bpm"))),
            isrc=self._get_first(audio.get("isrc")),
            key_camelot=self._get_first(audio.get("initialkey")),
        )

    def _extract_opus(self, file_path: Path) -> TrackMetadata:
        """Extract Opus metadata."""
        try:
            audio = OggOpus(file_path)
        except Exception:
            return TrackMetadata()

        return TrackMetadata(
            title=self._get_first(audio.get("title")),
            artist=self._get_first(audio.get("artist")),
            album=self._get_first(audio.get("album")),
            genre=self._get_first(audio.get("genre")),
            bpm=self._parse_int(self._get_first(audio.get("bpm"))),
            isrc=self._get_first(audio.get("isrc")),
            key_camelot=self._get_first(audio.get("initialkey")),
        )

    def _extract_mp4(self, file_path: Path) -> TrackMetadata:
        """Extract MP4 (M4A) metadata."""
        try:
            audio = MP4(file_path)
        except Exception:
            return TrackMetadata()

        return TrackMetadata(
            title=self._get_first(audio.get("\xa9nam")),
            artist=self._get_first(audio.get("\xa9ART")),
            album=self._get_first(audio.get("\xa9alb")),
            genre=self._get_first(audio.get("\xa9gen")),
            bpm=self._parse_int(self._get_first(audio.get("tmpo"))),
            isrc=self._get_first(audio.get("isrc")),
            key_camelot=self._get_first(audio.get("\xa9key")),
        )

    def _extract_wave(self, file_path: Path) -> TrackMetadata:
        """Extract WAV metadata."""
        try:
            audio = WAVE(file_path)
        except Exception:
            return TrackMetadata()

        # WAV files typically use ID3 tags
        return TrackMetadata(
            title=self._get_first(audio.get("TIT2")),
            artist=self._get_first(audio.get("TPE1")),
            album=self._get_first(audio.get("TALB")),
            genre=self._get_first(audio.get("TCON")),
            bpm=self._parse_int(self._get_first(audio.get("TBPM"))),
            isrc=self._get_first(audio.get("TSRC")),
        )

    def _extract_aiff(self, file_path: Path) -> TrackMetadata:
        """Extract AIFF metadata."""
        try:
            audio = AIFF(file_path)
        except Exception:
            return TrackMetadata()

        return TrackMetadata(
            title=self._get_first(audio.get("TIT2")),
            artist=self._get_first(audio.get("TPE1")),
            album=self._get_first(audio.get("TALB")),
            genre=self._get_first(audio.get("TCON")),
            bpm=self._parse_int(self._get_first(audio.get("TBPM"))),
            isrc=self._get_first(audio.get("TSRC")),
        )

    def _extract_audio_info(self, file_path: Path) -> Optional[TrackMetadata]:
        """Extract audio properties (sample rate, bitrate, channels) from file."""
        try:
            from mutagen.File import File
            audio = File(file_path)
            if not audio or not audio.info:
                return None

            info = audio.info
            return TrackMetadata(
                duration_seconds=float(info.length) if hasattr(info, "length") else None,
                sample_rate=getattr(info, "sample_rate", None),
                bitrate=int(getattr(info, "bitrate", 0) / 1000) if getattr(info, "bitrate", 0) else None,
                channels=getattr(info, "channels", None),
            )
        except Exception as e:
            self.logger.debug(f"Could not extract audio info from {file_path}: {e}")
            return None

    @staticmethod
    def _get_first(value: Any) -> Optional[str]:
        """Get first element from list or return string as-is."""
        if isinstance(value, list) and value:
            return str(value[0])
        if isinstance(value, str):
            return value if value.strip() else None
        return None

    @staticmethod
    def _parse_int(value: Optional[str]) -> Optional[int]:
        """
        Parse integer from string.

        BPM tags are commonly written as decimals (TBPM="128.00"), so parse as a
        float first and round rather than rejecting the value.
        """
        if value is None:
            return None
        try:
            return round(float(value))
        except (ValueError, TypeError):
            return None
