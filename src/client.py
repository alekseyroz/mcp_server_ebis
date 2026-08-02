"""HTTP client for Veryon Workcenter (WC) API."""

from base64 import b64encode
from typing import Any

import httpx

from .config import BASE_URL, PASSWORD, USERNAME


def get_auth_headers() -> dict[str, str]:
    """Generate Basic auth headers."""
    token = b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def get(endpoint: str, params: dict | None = None) -> Any:
    """Make GET request to WC API."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/{endpoint}",
            headers=get_auth_headers(),
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


def post(endpoint: str, body: dict) -> Any:
    """Make POST request to WC API."""
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{BASE_URL}/{endpoint}",
            headers={**get_auth_headers(), "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()
