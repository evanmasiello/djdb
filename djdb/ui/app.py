from __future__ import annotations

from pathlib import Path


class AppWindow:
    """Thin desktop shell for the DJ DB UI.

    This PR intentionally keeps the shell minimal: it loads a basic HTML template,
    exposes start/stop lifecycle methods, and does not add packaging or ingestion logic.
    """

    def __init__(self, title: str = "DJ DB") -> None:
        self.title = title
        self.template = """
        <html>
          <body>
            <div class="search">Search</div>
            <div class="library">Library</div>
          </body>
        </html>
        """

    def load_html(self) -> str:
        return self.template

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None
