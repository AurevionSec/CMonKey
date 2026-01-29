"""
AURENET - HTTP Client Abstraction

Provides abstraction layer for HTTP operations.
This allows mocking in tests and centralizes HTTP logic.
"""

from typing import Protocol, Dict, Any, Optional
import requests
from requests import Response


class HttpClient(Protocol):
    """Protocol for HTTP operations."""

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Response:
        """Perform HTTP GET request."""
        ...


class RequestsHttpClient:
    """Real HTTP client using requests library."""

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Response:
        return requests.get(url, headers=headers or {}, params=params or {}, timeout=timeout)


class MockHttpClient:
    """Mock HTTP client for testing."""

    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        self._responses = responses or {}
        self._call_history: list[tuple[str, Dict, Dict]] = []

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Response:
        # Record call
        self._call_history.append((url, headers or {}, params or {}))

        # Return mock response
        if url in self._responses:
            response = Response()
            response.status_code = 200
            response._content = str(self._responses[url]).encode()
            return response

        # Default response
        response = Response()
        response.status_code = 404
        return response

    def get_call_history(self) -> list[tuple[str, Dict, Dict]]:
        """Get history of HTTP calls for testing."""
        return self._call_history
