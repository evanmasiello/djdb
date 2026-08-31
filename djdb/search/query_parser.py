import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class QuerySpec:
    semantic_query: str
    artist: Optional[str] = None
    bpm_range: Optional[Tuple[int, int]] = None
    key: Optional[str] = None
    genre: Optional[str] = None


class QueryParser:
    """Parse user search queries into structured, metadata-aware filters."""

    GENRE_KEYWORDS = {
        "house",
        "techno",
        "trance",
        "drum and bass",
        "drum-and-bass",
        "dubstep",
        "garage",
        "minimal",
        "acid",
        "disco",
        "funk",
        "deep house",
        "progressive",
        "tech house",
        "electro",
        "hip hop",
        "hip-hop",
    }

    def parse(self, query: str) -> QuerySpec:
        if query is None:
            query = ""

        raw_query = query.strip()
        if not raw_query:
            return QuerySpec(semantic_query="")

        artist = self._extract_artist(raw_query)
        bpm_range = self._extract_bpm_range(raw_query)
        key = self._extract_key(raw_query)
        genre = self._extract_genre(raw_query)

        clean_query = raw_query

        if artist:
            clean_query = re.sub(rf"(?i)\bby\s+{re.escape(artist)}\b", "", clean_query)
            clean_query = re.sub(rf"(?i)\b{re.escape(artist)}\b", "", clean_query)

        if bpm_range:
            clean_query = re.sub(r"(?i)\b(?:around|about|approx(?:imately)?)?\s*(?:bpm\s*)?\d{2,3}\s*(?:-|to)\s*\d{2,3}\s*(?:bpm)?\b", "", clean_query)
            clean_query = re.sub(r"(?i)\b(?:around|about|approx(?:imately)?)\s*(?:bpm\s*)?\d{2,3}\s*(?:bpm)?\b", "", clean_query)
            clean_query = re.sub(r"(?i)\bbpm\s*\d{2,3}\b", "", clean_query)

        if key:
            clean_query = re.sub(rf"(?i)\b(?:key\s+)?{re.escape(key)}\b", "", clean_query)
            clean_query = re.sub(r"(?i)(?<=\w)key\b", " ", clean_query)

        clean_query = re.sub(r"(?i)(?<=\w)(?:genre|by|key|bpm)\b", " ", clean_query)
        clean_query = re.sub(r"(?i)\b[A-G]\s*(?:major|minor)\b", "", clean_query)
        clean_query = re.sub(r"\s+", " ", clean_query).strip(" ,.-")

        semantic_query = clean_query or self._fallback_semantic_query(raw_query)
        return QuerySpec(
            semantic_query=semantic_query,
            artist=artist,
            bpm_range=bpm_range,
            key=key,
            genre=genre,
        )

    def _fallback_semantic_query(self, query: str) -> str:
        cleaned = re.sub(r"(?i)\b(?:by|key|genre|bpm)\b", "", query)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
        return cleaned

    def _extract_artist(self, query: str) -> Optional[str]:
        match = re.search(r"(?i)\bby\s+([A-Z][A-Za-z0-9&'\-\. ]+?)(?=\s+\b(?:bpm|key|genre)\b|$)", query)
        if match:
            return match.group(1).strip()
        return None

    def _extract_bpm_range(self, query: str) -> Optional[Tuple[int, int]]:
        range_match = re.search(
            r"(?i)\b(?:around|about|approx(?:imately)?)?\s*(\d{2,3})\s*(?:-|\s*to\s*)\s*(\d{2,3})\s*bpm\b",
            query,
        )
        if range_match:
            low = int(range_match.group(1))
            high = int(range_match.group(2))
            return (low, high)

        range_match = re.search(r"(?i)\bbpm\s*(\d{2,3})\s*(?:-|\s*to\s*)\s*(\d{2,3})\b", query)
        if range_match:
            low = int(range_match.group(1))
            high = int(range_match.group(2))
            return (low, high)

        single_match = re.search(r"(?i)\b(?:around|about|approx(?:imately)?)\s*(\d{2,3})\s*bpm\b", query)
        if single_match:
            base = int(single_match.group(1))
            return (max(0, base - 8), base + 8)

        single_match = re.search(r"(?i)\bbpm\s*(\d{2,3})\b", query)
        if single_match:
            base = int(single_match.group(1))
            return (max(0, base - 8), base + 8)

        return None

    def _extract_key(self, query: str) -> Optional[str]:
        match = re.search(r"(?i)\b(?:key\s+)?([1-9]|1[0-2])([A-B])\b", query)
        if match:
            return f"{match.group(1)}{match.group(2).upper()}"
        return None

    def _extract_genre(self, query: str) -> Optional[str]:
        lowered = query.lower()
        for genre in sorted(self.GENRE_KEYWORDS, key=len, reverse=True):
            if re.search(rf"(?i)\b{re.escape(genre)}\b", query):
                return genre
        return None
