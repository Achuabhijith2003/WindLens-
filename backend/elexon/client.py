"""HTTP client for interacting with Elexon BMRS API endpoints using HTTPX.

Provides robust timeout handling, status error translation, and clean JSON parsing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
DEFAULT_TIMEOUT_SECONDS = 30.0


class ElexonAPIError(Exception):
    """Base exception for Elexon API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class ElexonTimeoutError(ElexonAPIError):
    """Raised when an HTTP request to Elexon times out."""
    pass


class ElexonConnectionError(ElexonAPIError):
    """Raised when network connectivity to Elexon fails."""
    pass


class ElexonHTTPStatusError(ElexonAPIError):
    """Raised when Elexon returns an unexpected HTTP error code."""
    pass


def format_iso8601_utc(dt: datetime) -> str:
    """Format a datetime as an ISO 8601 UTC string (e.g. 2026-01-01T00:00:00Z)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonClient:
    """Client for Elexon BMRS API streams and dataset endpoints."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: Optional[httpx.Client] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        default_headers = {
            "Accept": "application/json",
            "User-Agent": "WindLens-Phase1-Client/1.0",
        }
        if headers:
            default_headers.update(headers)

        # Allow dependency injection of httpx.Client (e.g. for testing with MockTransport)
        self._external_client = client is not None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            headers=default_headers,
        )

    def close(self) -> None:
        """Close the underlying HTTP client if internally managed."""
        if not self._external_client:
            self._client.close()

    def __enter__(self) -> ElexonClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute HTTP request with clear error mapping.

        Returns a list of records extracted from the response JSON (whether array or {"data": [...]}).
        """
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        
        try:
            response = self._client.request(method, url, params=params)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            msg = f"Request to Elexon API timed out ({self.timeout}s): {url}"
            logger.error(msg)
            raise ElexonTimeoutError(msg) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            error_text = exc.response.text[:500] if exc.response.text else "No response body"
            msg = f"Elexon API returned HTTP {status} for {url}. Details: {error_text}"
            logger.error(msg)
            raise ElexonHTTPStatusError(msg, status_code=status, details=error_text) from exc
        except httpx.RequestError as exc:
            msg = f"Network communication error connecting to Elexon API: {url} ({type(exc).__name__}: {exc})"
            logger.error(msg)
            raise ElexonConnectionError(msg) from exc

        try:
            payload = response.json()
        except Exception as exc:
            msg = f"Failed to parse JSON response from Elexon API: {response.text[:200]}"
            logger.error(msg)
            raise ElexonAPIError(msg, status_code=response.status_code) from exc

        # Handle both direct JSON list `[...]` and envelope `{"data": [...]}`
        if isinstance(payload, list):
            return payload
        elif isinstance(payload, dict):
            if "data" in payload and isinstance(payload["data"], list):
                return payload["data"]
            # If a single dictionary is returned, wrap in a list
            return [payload]
        else:
            msg = f"Unexpected JSON payload type from Elexon API: {type(payload)}"
            logger.error(msg)
            raise ElexonAPIError(msg, details=payload)

    def fetch_fuelhh_stream(
        self,
        publish_from: datetime,
        publish_to: datetime,
        fuel_type: Optional[str] = "WIND",
        format_type: str = "json",
    ) -> List[Dict[str, Any]]:
        """Request FUELHH stream records for a publication-time range.

        Args:
            publish_from: Start of the publication datetime range (inclusive).
            publish_to: End of the publication datetime range (inclusive).
            fuel_type: Optional fuelType filter (default: "WIND").
            format_type: Output format (default: "json").

        Returns:
            List of raw record dictionaries from the stream.
        """
        params: Dict[str, Any] = {
            "publishDateTimeFrom": format_iso8601_utc(publish_from),
            "publishDateTimeTo": format_iso8601_utc(publish_to),
            "format": format_type,
        }
        if fuel_type:
            params["fuelType"] = fuel_type

        return self._request("GET", "datasets/FUELHH/stream", params=params)

    def fetch_windfor_stream(
        self,
        publish_from: datetime,
        publish_to: datetime,
        format_type: str = "json",
    ) -> List[Dict[str, Any]]:
        """Request WINDFOR stream records for a publication-time range.

        Args:
            publish_from: Start of the publication datetime range.
            publish_to: End of the publication datetime range.
            format_type: Output format (default: "json").

        Returns:
            List of raw WINDFOR forecast dictionaries.
        """
        params: Dict[str, Any] = {
            "publishDateTimeFrom": format_iso8601_utc(publish_from),
            "publishDateTimeTo": format_iso8601_utc(publish_to),
            "format": format_type,
        }
        return self._request("GET", "datasets/WINDFOR/stream", params=params)

