"""Logging configuration for the application."""

import logging
import logging.handlers
from pathlib import Path
from pythonjsonlogger import jsonlogger

from djdb.core.config import settings


def setup_logging():
    """Configure JSON logging to file and console."""
    log_dir = settings.app_data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    # File handler with JSON formatting
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "djdb.log",
        maxBytes=10485760,  # 10MB
        backupCount=5,
    )
    json_formatter = jsonlogger.JsonFormatter()
    file_handler.setFormatter(json_formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    return root_logger


logger = setup_logging()
