"""Database models for SQLite metadata storage."""

from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Track(Base):
    """Track metadata stored in SQLite."""
    __tablename__ = "tracks"

    # Primary identifier
    file_hash = Column(String(64), primary_key=True, doc="SHA-256 of full file contents")
    file_path = Column(String(1024), unique=True, nullable=False, doc="Absolute path to audio file")

    # Basic metadata
    title = Column(String(255), nullable=False)
    artist = Column(String(255), nullable=False)
    album = Column(String(255))
    genre = Column(String(100))

    # Musical properties
    bpm = Column(Integer)
    key_camelot = Column(String(10), doc="Camelot notation (e.g., '1A', '12B')")
    key_open = Column(String(10), doc="Open notation (e.g., 'C major', 'A minor')")
    duration_seconds = Column(Float)

    # File properties
    sample_rate = Column(Integer)
    bitrate = Column(Integer, doc="Bitrate in kbps")
    channels = Column(Integer)
    codec = Column(String(50))
    isrc = Column(String(12), doc="International Standard Recording Code")

    # User metadata
    tags = Column(Text, doc="JSON array of user-defined tags")
    rating = Column(Integer, doc="1-5 star rating")
    color_label = Column(String(50), doc="Color for visual organization")
    comments = Column(Text, doc="User notes")

    # Timestamps
    date_added = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    date_imported = Column(DateTime)

    # Quality analysis
    quality_notes = Column(Text, doc="Detailed quality analysis")
    quality_flag = Column(String(50), doc="e.g., 'lossy', 'lossless', 'upsampled'")

    # Import state from DJ software
    import_source = Column(String(50), doc="e.g., 'rekordbox', 'serato', 'virtualdj'")
    import_metadata = Column(Text, doc="JSON of original import data")

    # Embeddings
    embedding_model = Column(String(255), default="laion/larger_clap", doc="Model used for audio embedding")

    # Relationships
    lyrics = relationship("Lyrics", back_populates="track", uselist=False, cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="track", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_artist", "artist"),
        Index("ix_genre", "genre"),
        Index("ix_bpm", "bpm"),
        Index("ix_file_path", "file_path"),
    )


class Lyrics(Base):
    """Lyric content and metadata."""
    __tablename__ = "lyrics"

    file_hash = Column(String(64), ForeignKey("tracks.file_hash"), primary_key=True)
    lyrics_full = Column(Text, doc="Full lyric text")
    lyrics_snippet = Column(Text, doc="First 500 chars for display/search")
    lyrics_timestamps = Column(Text, doc="JSON: word-level timestamps from WhisperX")
    lyric_vector = Column(Text, doc="JSON array of float: semantic embedding of lyrics")
    transcription_model = Column(String(100), doc="e.g., 'whisperx-large'")
    transcription_confidence = Column(Float, doc="Average confidence score (0-1)")
    transcription_date = Column(DateTime)

    track = relationship("Track", back_populates="lyrics")


class Feedback(Base):
    """User feedback for model training and implicit signals."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    file_hash = Column(String(64), ForeignKey("tracks.file_hash"), nullable=False)
    feedback_type = Column(String(50), doc="e.g., 'play', 'skip', 'rate', 'cue'")
    feedback_value = Column(String(255), doc="e.g., rating value, cue point time")
    timestamp = Column(DateTime, default=datetime.utcnow)

    track = relationship("Track", back_populates="feedbacks")

    __table_args__ = (
        Index("ix_file_hash", "file_hash"),
        Index("ix_feedback_type", "feedback_type"),
    )


class LibraryImport(Base):
    """Track import state from DJ software."""
    __tablename__ = "library_imports"

    id = Column(Integer, primary_key=True)
    import_source = Column(String(50), nullable=False, doc="'rekordbox', 'serato', 'virtualdj'")
    import_date = Column(DateTime, default=datetime.utcnow)
    import_file_path = Column(String(1024), doc="Path to source file/folder")
    tracks_imported = Column(Integer, default=0)
    tracks_updated = Column(Integer, default=0)
    tracks_skipped = Column(Integer, default=0)
    import_notes = Column(Text)
