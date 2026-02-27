from __future__ import annotations

import http.server
import pathlib
import threading
from typing import Generator

import pytest

_MOCK_SITES_DIR = pathlib.Path(__file__).parent / "mock_sites"


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(_MOCK_SITES_DIR), **kwargs)  # type: ignore[arg-type]

    def log_message(self, *_args: object) -> None:
        pass


@pytest.fixture(scope="session")
def mock_site_server() -> Generator[str, None, None]:
    """Start a local HTTP server serving mock HTML pages."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _SilentHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
