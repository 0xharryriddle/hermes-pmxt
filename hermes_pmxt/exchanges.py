"""Exchange initialization, normalization, and sidecar helpers for pmxt."""

from __future__ import annotations

import os
import time
from typing import Optional

try:
    import pmxt
except ImportError as exc:
    raise ImportError(
        "pmxt is not installed. Run: pip install pmxt. "
        "Depending on your pmxt version, you may also need a pmxtjs sidecar."
    ) from exc


_exchange_cache: dict[str, object] = {}

EXCHANGES = (
    "polymarket",
    "polymarket_us",
    "kalshi",
    "limitless",
    "myriad",
    "opinion",
    "metaculus",
    "smarkets",
)

TRADING_EXCHANGES = (
    "polymarket",
    "polymarket_us",
    "kalshi",
    "limitless",
)

_ALIASES = {
    "polymarket-us": "polymarket_us",
    "polymarket us": "polymarket_us",
    "polymarketus": "polymarket_us",
}


def normalize_exchange_name(name: str) -> str:
    """Normalize a user-facing exchange name to the package's canonical form."""
    normalized = name.lower().strip().replace("-", "_")
    normalized = _ALIASES.get(normalized, normalized)
    return normalized.replace(" ", "_")


def _exchange_class(name: str):
    """Resolve the pmxt exchange class for a normalized exchange name."""
    normalized = normalize_exchange_name(name)
    class_name = "".join(part.capitalize() for part in normalized.split("_"))
    return getattr(pmxt, class_name, None)


def available_exchange_names() -> list[str]:
    """Return exchange names that appear to exist in the installed pmxt build."""
    return [name for name in EXCHANGES if _exchange_class(name) is not None]


def ensure_server() -> tuple[bool, Optional[str]]:
    """Ensure the pmxt sidecar server is running. Returns (ok, error_msg)."""
    try:
        if not pmxt.server.health():
            pmxt.server.start()
            time.sleep(1.5)
        if not pmxt.server.health():
            return False, "Sidecar server failed to start"
        return True, None
    except Exception as e:
        return False, f"Sidecar server error: {e}"


def get_exchange(name: str) -> tuple[Optional[object], Optional[str]]:
    """
    Get or initialize an exchange. Cached after first call.
    Returns (exchange_instance, error_msg).
    """
    normalized = normalize_exchange_name(name)

    if normalized in _exchange_cache:
        return _exchange_cache[normalized], None

    try:
        exchange = _create_exchange(normalized)
        _exchange_cache[normalized] = exchange
        return exchange, None
    except Exception as e:
        return None, f"Failed to initialize {normalized}: {e}"


def _create_exchange(name: str):
    """Instantiate an exchange by normalized name."""
    normalized = normalize_exchange_name(name)

    if normalized == "polymarket":
        return pmxt.Polymarket(
            private_key=os.getenv("POLYMARKET_PRIVATE_KEY"),
            proxy_address=os.getenv("POLYMARKET_PROXY_ADDRESS"),
            signature_type="gnosis-safe",
        )
    if normalized == "polymarket_us":
        cls = _exchange_class(normalized)
        if cls is None:
            raise ValueError("Exchange polymarket_us is not available in this pmxt version")
        return cls(
            api_key=os.getenv("POLYMARKET_US_API_KEY"),
            private_key=os.getenv("POLYMARKET_US_PRIVATE_KEY"),
        )
    if normalized == "kalshi":
        return pmxt.Kalshi(
            api_key=os.getenv("KALSHI_API_KEY"),
            private_key=os.getenv("KALSHI_PRIVATE_KEY"),
        )
    if normalized == "limitless":
        return pmxt.Limitless(
            api_key=os.getenv("LIMITLESS_API_KEY"),
            private_key=os.getenv("LIMITLESS_PRIVATE_KEY"),
        )

    cls = _exchange_class(normalized)
    if cls is None:
        raise ValueError(f"Unknown exchange: {normalized}")
    return cls()


def server_status() -> dict:
    """Get sidecar server status."""
    try:
        status = pmxt.server.status()
        if isinstance(status, dict):
            return {
                "running": status.get("running", False),
                "pid": status.get("pid"),
                "port": status.get("port"),
                "version": status.get("version"),
                "uptime_seconds": status.get("uptimeSeconds") or status.get("uptime_seconds"),
            }
        return {
            "running": getattr(status, "running", False),
            "pid": getattr(status, "pid", None),
            "port": getattr(status, "port", None),
            "version": getattr(status, "version", None),
            "uptime_seconds": getattr(status, "uptimeSeconds", None),
        }
    except Exception as e:
        return {"running": False, "error": str(e)}


def server_logs(n: int = 50) -> list[str]:
    """Get last N lines of server logs."""
    try:
        return list(pmxt.server.logs(n))
    except Exception:
        return []
