from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Query

from djdb.core.database import Track


@dataclass
class FilterCriteria:
    artist: Optional[str] = None
    bpm_min: Optional[int] = None
    bpm_max: Optional[int] = None
    key: Optional[str] = None
    genre: Optional[str] = None

    def is_empty(self) -> bool:
        return all(
            value is None or value == ""
            for value in (self.artist, self.bpm_min, self.bpm_max, self.key, self.genre)
        )


class MetadataFilter:
    """Apply metadata constraints to a SQLAlchemy query."""

    @staticmethod
    def apply(query: Query, criteria: FilterCriteria) -> Query:
        if criteria is None:
            return query

        if criteria.artist:
            query = query.filter_by(artist=criteria.artist)

        if criteria.bpm_min is not None:
            query = query.filter(Track.bpm >= criteria.bpm_min)

        if criteria.bpm_max is not None:
            query = query.filter(Track.bpm <= criteria.bpm_max)

        if criteria.key:
            query = query.filter_by(key_camelot=criteria.key)

        if criteria.genre:
            normalized = criteria.genre.strip().lower()
            query = query.filter(
                (Track.genre.ilike(f"%{normalized}%")) | (Track.tags.ilike(f"%{normalized}%"))
            )

        return query
