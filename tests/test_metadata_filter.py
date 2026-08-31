from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from djdb.core.database import Base, Track
from djdb.search.metadata_filter import FilterCriteria, MetadataFilter


def _seed_tracks() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)

    session.add_all(
        [
            Track(
                file_hash="a1",
                file_path="/music/track1.mp3",
                title="Track One",
                artist="Daft Punk",
                genre="House",
                bpm=124,
                key_camelot="8A",
                key_open="F# minor",
            ),
            Track(
                file_hash="b2",
                file_path="/music/track2.mp3",
                title="Track Two",
                artist="Disclosure",
                genre="Tech House",
                bpm=128,
                key_camelot="3A",
                key_open="C minor",
            ),
            Track(
                file_hash="c3",
                file_path="/music/track3.mp3",
                title="Track Three",
                artist="Daft Punk",
                genre="Disco",
                bpm=118,
                key_camelot="10B",
                key_open="G minor",
            ),
        ]
    )
    session.commit()
    return session


def test_metadata_filter_applies_artist_bpm_key_and_genre_constraints():
    session = _seed_tracks()

    criteria = FilterCriteria(
        artist="Daft Punk",
        bpm_min=120,
        bpm_max=126,
        key="8A",
        genre="house",
    )

    results = MetadataFilter.apply(session.query(Track), criteria).all()

    assert len(results) == 1
    assert results[0].file_hash == "a1"


def test_metadata_filter_allows_empty_criteria():
    session = _seed_tracks()

    results = MetadataFilter.apply(session.query(Track), FilterCriteria()).all()

    assert len(results) == 3
