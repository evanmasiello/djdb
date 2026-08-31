"""DJ software metadata import utilities."""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import unquote

from djdb.ingestion.metadata_extractor import TrackMetadata

logger = logging.getLogger(__name__)


def _parse_float(value: Optional[str]) -> Optional[float]:
    """Parse a float from an XML attribute, returning None if it is absent or malformed."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    """
    Parse an integer from an XML attribute.

    DJ software writes whole-number fields as decimals (Rekordbox emits
    AverageBpm="128.00"), so parse as a float first and round.
    """
    parsed = _parse_float(value)
    return None if parsed is None else round(parsed)


@dataclass
class ImportedTrack:
    """Track metadata imported from DJ software."""
    file_path: str
    metadata: TrackMetadata
    source: str  # 'rekordbox', 'serato', 'virtualdj'
    import_date: datetime
    original_data: Dict[str, Any]


class RekordboxImporter:
    """Import tracks from Rekordbox XML export."""

    def __init__(self):
        """Initialize Rekordbox importer."""
        self.logger = logging.getLogger(__name__)

    def import_xml(self, xml_path: Path) -> Iterator[ImportedTrack]:
        """
        Import tracks from Rekordbox XML export.
        
        Args:
            xml_path: Path to Rekordbox export.xml
            
        Yields:
            ImportedTrack objects
        """
        if not xml_path.exists():
            raise FileNotFoundError(f"File not found: {xml_path}")

        self.logger.info(f"Importing from Rekordbox XML: {xml_path}")

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse XML: {e}")
            return

        # Rekordbox structure: <DJ_PLAYLISTS><COLLECTION><TRACK .../></COLLECTION>.
        # Element names are uppercase. Scope the search to COLLECTION because
        # <PLAYLISTS> repeats each track as a bare <TRACK Key="..."/> reference.
        track_elems = root.findall("./COLLECTION/TRACK")
        if not track_elems:
            track_elems = root.findall(".//TRACK")

        for track_elem in track_elems:
            try:
                track = self._parse_track(track_elem)
                if track:
                    yield track
            except Exception as e:
                self.logger.error(f"Error parsing track: {e}")
                continue

    def _parse_track(self, track_elem: ET.Element) -> Optional[ImportedTrack]:
        """Parse Rekordbox track XML element."""
        # Location is a percent-encoded file URI, e.g.
        # "file://localhost/Users/me/Music/My%20Track.mp3".
        location = track_elem.get("Location", "")
        if not location:
            return None
        location = unquote(location.replace("file://localhost", ""))

        try:
            # Parse metadata from track attributes and subelements
            metadata = TrackMetadata(
                title=track_elem.get("Name"),
                artist=track_elem.get("Artist"),
                album=track_elem.get("Album"),
                genre=track_elem.get("Genre"),
                bpm=_parse_int(track_elem.get("AverageBpm")),
                duration_seconds=_parse_float(track_elem.get("TotalTime")),
                key_camelot=track_elem.get("Tonality"),
                bitrate=_parse_int(track_elem.get("Bitrate")),
                isrc=track_elem.get("ISRC"),
            )

            original_data = {
                "location": location,
                "trackid": track_elem.get("TrackID"),
                "dateadded": track_elem.get("DateAdded"),
                "lastmodified": track_elem.get("LastModified"),
                "playcount": track_elem.get("PlayCount"),
                "rating": track_elem.get("Rating"),
                "comments": track_elem.get("Comments"),
                "color": track_elem.get("Color"),
            }

            return ImportedTrack(
                file_path=location,
                metadata=metadata,
                source="rekordbox",
                import_date=datetime.now(),
                original_data=original_data,
            )
        except Exception as e:
            self.logger.error(f"Error parsing track element: {e}")
            return None


class SeratoImporter:
    """Import tracks from Serato database."""

    def __init__(self):
        """Initialize Serato importer."""
        self.logger = logging.getLogger(__name__)

    def import_database(self, serato_folder: Path) -> Iterator[ImportedTrack]:
        """
        Import tracks from Serato database folder.
        
        Args:
            serato_folder: Path to Serato data folder (usually ~/_Serato_/)
            
        Yields:
            ImportedTrack objects
        """
        if not serato_folder.exists():
            raise FileNotFoundError(f"Folder not found: {serato_folder}")

        self.logger.info(f"Importing from Serato: {serato_folder}")

        # Serato stores metadata in various .db files.
        # Full database parsing is not implemented for the MVP, so return an empty iterator.
        library_db_path = serato_folder / "library.db"

        if not library_db_path.exists():
            self.logger.warning(f"Serato library database not found: {library_db_path}")
            return iter(())

        # Note: Full Serato .db parsing requires reverse-engineering their binary format.
        # For now, this is a placeholder that logs the limitation and yields nothing.
        self.logger.info(
            "Full Serato .db parsing requires reverse-engineering Serato's binary format. "
            "Consider using Serato's XML export feature instead."
        )
        return iter(())

    def import_xml(self, xml_path: Path) -> Iterator[ImportedTrack]:
        """
        Import tracks from Serato XML export.
        
        Args:
            xml_path: Path to Serato XML export
            
        Yields:
            ImportedTrack objects
        """
        if not xml_path.exists():
            raise FileNotFoundError(f"File not found: {xml_path}")

        self.logger.info(f"Importing from Serato XML: {xml_path}")

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse XML: {e}")
            return

        # Serato XML structure varies; this is a basic parser
        for track_elem in root.findall(".//TRACK"):
            try:
                track = self._parse_track(track_elem)
                if track:
                    yield track
            except Exception as e:
                self.logger.error(f"Error parsing track: {e}")
                continue

    def _parse_track(self, track_elem: ET.Element) -> Optional[ImportedTrack]:
        """Parse Serato track XML element."""
        location = track_elem.findtext("LOCATION")
        if not location:
            return None

        try:
            metadata = TrackMetadata(
                title=track_elem.findtext("TITLE"),
                artist=track_elem.findtext("ARTIST"),
                album=track_elem.findtext("ALBUM"),
                genre=track_elem.findtext("GENRE"),
                bpm=_parse_int(track_elem.findtext("BPM")),
                duration_seconds=_parse_float(track_elem.findtext("DURATION")),
                key_camelot=track_elem.findtext("KEY"),
                comments=track_elem.findtext("COMMENTS"),
            )

            original_data = {
                "location": location,
                "comments": track_elem.findtext("COMMENTS"),
                "cues": track_elem.findtext("CUE_POINTS"),
            }

            return ImportedTrack(
                file_path=location,
                metadata=metadata,
                source="serato",
                import_date=datetime.now(),
                original_data=original_data,
            )
        except Exception as e:
            self.logger.error(f"Error parsing track element: {e}")
            return None


class VirtualDJImporter:
    """Import tracks from Virtual DJ database."""

    def __init__(self):
        """Initialize Virtual DJ importer."""
        self.logger = logging.getLogger(__name__)

    def import_xml(self, xml_path: Path) -> Iterator[ImportedTrack]:
        """
        Import tracks from Virtual DJ database XML.
        
        Args:
            xml_path: Path to Virtual DJ database.xml
            
        Yields:
            ImportedTrack objects
        """
        if not xml_path.exists():
            raise FileNotFoundError(f"File not found: {xml_path}")

        self.logger.info(f"Importing from Virtual DJ XML: {xml_path}")

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse XML: {e}")
            return

        # Virtual DJ structure: <VirtualDJ><Database><Folders><Folder><Playlist><Song>
        for song_elem in root.findall(".//Song"):
            try:
                track = self._parse_track(song_elem)
                if track:
                    yield track
            except Exception as e:
                self.logger.error(f"Error parsing track: {e}")
                continue

    def _parse_track(self, song_elem: ET.Element) -> Optional[ImportedTrack]:
        """Parse Virtual DJ song XML element."""
        location = song_elem.get("Path")
        if not location:
            return None

        try:
            metadata = TrackMetadata(
                title=song_elem.get("Title"),
                artist=song_elem.get("Artist"),
                album=song_elem.get("Album"),
                genre=song_elem.get("Genre"),
                bpm=_parse_int(song_elem.get("BPM")),
                duration_seconds=_parse_float(song_elem.get("Duration")),
                key_camelot=song_elem.get("Key"),
                bitrate=_parse_int(song_elem.get("Bitrate")),
                comments=song_elem.get("Comments"),
            )

            original_data = {
                "location": location,
                "comments": song_elem.get("Comments"),
                "lastmodified": song_elem.get("LastModified"),
                "rating": song_elem.get("Rating"),
                "tags": song_elem.get("Tags"),
            }

            return ImportedTrack(
                file_path=location,
                metadata=metadata,
                source="virtualdj",
                import_date=datetime.now(),
                original_data=original_data,
            )
        except Exception as e:
            self.logger.error(f"Error parsing track element: {e}")
            return None
