from djdb.core.config import settings
from djdb.core.logging import setup_logging


def main() -> None:
    """Application startup entry point for packaging and CLI launch."""
    setup_logging()
    print(f"Starting {settings.app_name} on {settings.api_host}:{settings.api_port}")


if __name__ == "__main__":
    main()
