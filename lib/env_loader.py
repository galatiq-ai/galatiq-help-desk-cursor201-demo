"""Choose the ticket backend and load ZAMMAD_URL / ZAMMAD_API_TOKEN from a gitignored .env file.

Participants have no Zammad: when both values are blank (or missing), or ZAMMAD_LOCAL=1, the
helper uses the local desk in data/desk/tickets.json.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    env_path = path or Path(os.environ.get("ZAMMAD_ENV_FILE", REPO_ROOT / ".env"))
    out: dict[str, str] = {}
    if not env_path.is_file():
        return out
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def require_zammad_env() -> tuple[str, str]:
    merged = {**load_dotenv(), **{k: v for k, v in os.environ.items() if k.startswith("ZAMMAD_")}}
    url = merged.get("ZAMMAD_URL", "").rstrip("/")
    token = merged.get("ZAMMAD_API_TOKEN", "")
    if not url or not token:
        raise SystemExit(
            "Missing ZAMMAD_URL or ZAMMAD_API_TOKEN. Copy .env.example to .env and fill in values."
        )
    return url, token


def zammad_env() -> tuple[str, str] | None:
    """(url, token) when a real Zammad is configured, else None (use the local desk)."""
    if os.environ.get("ZAMMAD_LOCAL", "").strip().lower() in {"1", "true", "yes"}:
        return None
    merged = {**load_dotenv(), **{k: v for k, v in os.environ.items() if k.startswith("ZAMMAD_")}}
    url = merged.get("ZAMMAD_URL", "").rstrip("/")
    token = merged.get("ZAMMAD_API_TOKEN", "")
    if not url or not token:
        return None
    return url, token


def desk_backend() -> str:
    """"zammad" when both values are set (and ZAMMAD_LOCAL is not 1), otherwise "local"."""
    return "zammad" if zammad_env() else "local"
