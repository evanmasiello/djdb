"""Complete ingestion pipeline for tracks."""

import logging
from pathlib import Path
from typing import Optional, Iterator, Dict, Any
from datetime import datetime
from dataclasses import asdict

from sqlalchemy.orm import Session

from djdb.core.config import settings
from djdb.core.database import Track, LibraryImport
from djdb.core.database_init import get_session
from djdb.ingestion.scanner import AudioScanner
from djdb.ingestion.metadata_extractor import MetadataExtractor
from djdb.ingestion.dj_import import (
    RekordboxImporter,
    SeratoImporter,
    VirtualDJImporter,
    ImportedTrack,
)
from djdb.models.embedding_generator import EmbeddingGenerator
from djdb.models.vector_store import VectorStore

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrate audio file ingestion, metadata extraction, and embedding generation."""

    def __init__(
        self,
        embedding_model: str = "laion/larger_clap",
        collection_name: str = "tracks",
    ):
        """
        Initialize ingestion pipeline.
        
        Args:
            embedding_model: Hugging Face model ID for embeddings
            collection_name: ChromaDB collection name
        """
        self.logger = logging.getLogger(__name__)
        self.collection_name = collection_name
        
        # Initialize components
        self.scanner = AudioScanner()
        self.metadata_extractor = MetadataExtractor()
        self.embedding_generator = EmbeddingGenerator(embedding_model)
        self.vector_store = VectorStore()
        
        self.logger.info("Ingestion pipeline initialized")

    def ingest_directory(
        self,
        directory: Path,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        Scan directory and ingest all audio files.
        
        Args:
            directory: Path to directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            Statistics dictionary with counts of processed/failed tracks
        """
        stats = {
            "total_scanned": 0,
            "metadata_extracted": 0,
            "embeddings_generated": 0,
            "stored": 0,
            "failed": 0,
            "duplicates_updated": 0,
            "errors": [],
        }

        self.logger.info(f"Starting directory ingestion: {directory}")

        # Session for database operations
        session = next(get_session())

        try:
            for audio_file in self.scanner.scan_directory(directory, recursive):
                stats["total_scanned"] += 1
                
                try:
                    # Check if file already exists
                    existing_track = session.query(Track).filter_by(
                        file_hash=audio_file.file_hash
                    ).first()

                    if existing_track:
                        # Update existing track if file path changed
                        self.logger.info(
                            f"Updating existing track: {audio_file.path.name}"
                        )
                        existing_track.file_path = str(audio_file.path)
                        existing_track.date_modified = datetime.utcnow()
                        stats["duplicates_updated"] += 1
                    else:
                        # Extract metadata
                        metadata = self.metadata_extractor.extract(audio_file.path)
                        stats["metadata_extracted"] += 1

                        # Generate embedding
                        embedding = self.embedding_generator.generate_audio_embedding(
                            audio_file.path
                        )
                        if not embedding:
                            self.logger.warning(
                                f"Failed to generate embedding for {audio_file.path}"
                            )
                            stats["failed"] += 1
                            continue

                        stats["embeddings_generated"] += 1

                        # Create track record
                        track = Track(
                            file_hash=audio_file.file_hash,
                            file_path=str(audio_file.path),
                            title=metadata.title or audio_file.path.stem,
                            artist=metadata.artist or "Unknown",
                            album=metadata.album,
                            genre=metadata.genre,
                            bpm=metadata.bpm,
                            key_camelot=metadata.key_camelot,
                            key_open=metadata.key_open,
                            duration_seconds=metadata.duration_seconds,
                            sample_rate=metadata.sample_rate,
                            bitrate=metadata.bitrate,
                            channels=metadata.channels,
                            codec=metadata.codec or audio_file.codec,
                            isrc=metadata.isrc,
                            date_added=datetime.utcnow(),
                            embedding_model="laion/larger_clap",
                        )
                        session.add(track)

                        # Add to ChromaDB
                        metadata_dict = {
                            k: v for k, v in asdict(metadata).items()
                            if v is not None and k not in ["key_camelot", "key_open"]
                        }
                        metadata_dict["key_camelot"] = metadata.key_camelot
                        metadata_dict["key_open"] = metadata.key_open
                        metadata_dict["file_path"] = str(audio_file.path)

                        self.vector_store.add_embedding(
                            collection_name=self.collection_name,
                            track_id=audio_file.file_hash,
                            embedding=embedding,
                            metadata=metadata_dict,
                        )

                        stats["stored"] += 1
                        self.logger.info(
                            f"Ingested: {metadata.artist} - {metadata.title}"
                        )

                except Exception as e:
                    self.logger.error(f"Error ingesting {audio_file.path}: {e}")
                    stats["failed"] += 1
                    stats["errors"].append(str(e))
                    continue

            # Commit database changes
            session.commit()
            self.vector_store.persist()

            self.logger.info(f"Directory ingestion complete. Stats: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"Fatal error during ingestion: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def ingest_from_rekordbox(self, xml_path: Path) -> Dict[str, Any]:
        """
        Import tracks from Rekordbox export.
        
        Args:
            xml_path: Path to Rekordbox export.xml
            
        Returns:
            Statistics dictionary
        """
        stats = {
            "imported": 0,
            "failed": 0,
            "duplicates": 0,
            "errors": [],
        }

        importer = RekordboxImporter()
        session = next(get_session())

        try:
            for imported_track in importer.import_xml(xml_path):
                try:
                    self._ingest_imported_track(imported_track, session, stats)
                except Exception as e:
                    self.logger.error(f"Error importing track: {e}")
                    stats["failed"] += 1
                    stats["errors"].append(str(e))

            session.commit()
            self.logger.info(f"Rekordbox import complete. Stats: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"Fatal error during Rekordbox import: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def ingest_from_serato(self, input_path: Path) -> Dict[str, Any]:
        """
        Import tracks from Serato.
        
        Args:
            input_path: Path to Serato export XML or _Serato_ folder
            
        Returns:
            Statistics dictionary
        """
        stats = {
            "imported": 0,
            "failed": 0,
            "duplicates": 0,
            "errors": [],
        }

        importer = SeratoImporter()
        session = next(get_session())

        try:
            if input_path.is_dir():
                imported_tracks = importer.import_database(input_path)
            else:
                imported_tracks = importer.import_xml(input_path)

            for imported_track in imported_tracks:
                try:
                    self._ingest_imported_track(imported_track, session, stats)
                except Exception as e:
                    self.logger.error(f"Error importing track: {e}")
                    stats["failed"] += 1
                    stats["errors"].append(str(e))

            session.commit()
            self.logger.info(f"Serato import complete. Stats: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"Fatal error during Serato import: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def ingest_from_virtualdj(self, xml_path: Path) -> Dict[str, Any]:
        """
        Import tracks from Virtual DJ.
        
        Args:
            xml_path: Path to Virtual DJ database.xml
            
        Returns:
            Statistics dictionary
        """
        stats = {
            "imported": 0,
            "failed": 0,
            "duplicates": 0,
            "errors": [],
        }

        importer = VirtualDJImporter()
        session = next(get_session())

        try:
            for imported_track in importer.import_xml(xml_path):
                try:
                    self._ingest_imported_track(imported_track, session, stats)
                except Exception as e:
                    self.logger.error(f"Error importing track: {e}")
                    stats["failed"] += 1
                    stats["errors"].append(str(e))

            session.commit()
            self.logger.info(f"Virtual DJ import complete. Stats: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"Fatal error during Virtual DJ import: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def _ingest_imported_track(
        self,
        imported_track: ImportedTrack,
        session: Session,
        stats: Dict[str, Any],
    ) -> None:
        """
        Ingest a single track from DJ software import.
        
        Args:
            imported_track: ImportedTrack object
            session: SQLAlchemy session
            stats: Statistics dictionary to update
        """
        file_path = Path(imported_track.file_path)

        # Check if file exists
        if not file_path.exists():
            self.logger.warning(f"File not found: {file_path}")
            stats["failed"] += 1
            return

        # Check if track already exists
        existing = session.query(Track).filter_by(
            file_path=str(file_path)
        ).first()

        if existing:
            # Update existing track with imported metadata
            existing.title = imported_track.metadata.title or existing.title
            existing.artist = imported_track.metadata.artist or existing.artist
            existing.album = imported_track.metadata.album or existing.album
            existing.genre = imported_track.metadata.genre or existing.genre
            existing.bpm = imported_track.metadata.bpm or existing.bpm
            existing.key_camelot = imported_track.metadata.key_camelot or existing.key_camelot
            existing.key_open = imported_track.metadata.key_open or existing.key_open
            existing.bitrate = imported_track.metadata.bitrate or existing.bitrate
            existing.comments = imported_track.metadata.comments or existing.comments
            existing.date_imported = imported_track.import_date
            existing.import_source = imported_track.source
            stats["duplicates"] += 1
            self.logger.info(f"Updated existing track: {file_path.name}")
        else:
            # Create new track record
            track = Track(
                file_hash=self._compute_file_hash(file_path),
                file_path=str(file_path),
                title=imported_track.metadata.title or file_path.stem,
                artist=imported_track.metadata.artist or "Unknown",
                album=imported_track.metadata.album,
                genre=imported_track.metadata.genre,
                bpm=imported_track.metadata.bpm,
                key_camelot=imported_track.metadata.key_camelot,
                key_open=imported_track.metadata.key_open,
                duration_seconds=imported_track.metadata.duration_seconds,
                bitrate=imported_track.metadata.bitrate,
                comments=imported_track.metadata.comments,
                date_imported=imported_track.import_date,
                import_source=imported_track.source,
                import_metadata=str(imported_track.original_data),
            )
            session.add(track)
            stats["imported"] += 1
            self.logger.info(f"Imported: {imported_track.metadata.artist} - {imported_track.metadata.title}")

    @staticmethod
    def _compute_file_hash(file_path: Path, chunk_size: int = 65536) -> str:
        """Compute SHA-256 hash of file."""
        import hashlib
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
