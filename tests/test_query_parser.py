from djdb.search.query_parser import QueryParser, QuerySpec


def test_parse_extracts_metadata_filters_and_semantic_terms():
    parser = QueryParser()

    result = parser.parse("dark brooding house by Daft Punk bpm 120-128 key 8A")

    assert isinstance(result, QuerySpec)
    assert result.semantic_query == "dark brooding house"
    assert result.artist == "Daft Punk"
    assert result.bpm_range == (120, 128)
    assert result.key == "8A"
    assert result.genre == "house"


def test_parse_handles_around_bpm_and_open_key_notation():
    parser = QueryParser()

    result = parser.parse("around 128 bpm, melodic techno with a C minor mood")

    assert result.bpm_range == (120, 136)
    assert result.semantic_query == "melodic techno with a mood"
    assert result.key is None
    assert result.genre == "techno"


def test_parse_returns_empty_query_when_no_terms_are_present():
    parser = QueryParser()

    result = parser.parse("   ")

    assert result.semantic_query == ""
    assert result.artist is None
    assert result.bpm_range is None
    assert result.key is None
    assert result.genre is None
