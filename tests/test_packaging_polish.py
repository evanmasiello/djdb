from djdb.__main__ import main
from djdb.core.logging import setup_logging
from djdb.core.config import settings


def test_logging_setup_and_app_config_are_available():
    logger = setup_logging()
    assert logger is not None
    assert settings.app_name == "DJ DB"
    assert settings.api_host == "127.0.0.1"


def test_main_entrypoint_is_callable():
    assert callable(main)
