"""Configuration management for eBis Cloud API."""

import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Populate os.environ from a simple KEY=VALUE .env file, without overriding existing vars."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = os.environ.get("EBIS_BASE_URL", "https://ia.ebis5.com/api/integration/external")
USERNAME = os.environ.get("EBIS_USERNAME")
PASSWORD = os.environ.get("EBIS_PASSWORD")

if not USERNAME or not PASSWORD:
    raise RuntimeError(
        "EBIS_USERNAME and EBIS_PASSWORD must be set — copy .env.example to .env and fill them in."
    )
