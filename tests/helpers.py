"""Test-Hilfen: gefälschte HTTP-Session ohne Netzwerk."""
from __future__ import annotations

from pathlib import Path

import requests

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, status_code=200, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = content.decode("utf-8", "replace")


class FakeSession:
    """routes: url -> FakeResponse | Exception | callable(headers)->FakeResponse"""

    def __init__(self, routes=None, default=None):
        self.routes = routes or {}
        self.default = default
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, headers=None, timeout=None, stream=False):
        self.calls.append((url, dict(headers or {})))
        r = self.routes.get(url, self.default)
        if r is None:
            raise requests.ConnectionError(f"keine Route für {url}")
        if isinstance(r, Exception):
            raise r
        if callable(r):
            return r(headers or {})
        return r
