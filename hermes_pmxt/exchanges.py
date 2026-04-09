"""
Exchange initialization and caching for pmxt.

Handles lazy init, caching, and error resilience per exchange.
"""

import os
import time
from typing import Optional

try:
    import pmxt
except ImportError:
    raise ImportError(
        "pmxt is not installed. Run: pip install pmxt && npm install -g pmxtjs"
    )


_exchange_cache = {}

# Supported exchanges
EXCHANGES = {
    "polymarket",
    "kalshi",
    "limitless",
    "metaculus",
    "myriad",
    "opinion",
    "smarkets",
}


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
    name = name.lower().strip()

    if name in _exchange_cache:
        return _exchange_cache[name], None

    try:
        exchange = _create_exchange(name)
        _exchange_cache[name] = exchange
        return exchange, None
    except Exception as e:
        return None, f"Failed to initialize {name}: {e}"


def _create_exchange(name: str):
    """Instantiate an exchange by name."""
    if name == "polymarket":
        return pmxt.Polymarket(
            private_key=os.getenv("POLYMARKET_PRIVATE_KEY"),
            proxy_address=os.getenv("POLYMARKET_PROXY_ADDRESS"),
            signature_type="gnosis-safe",
        )
    elif name == "kalshi":
        return pmxt.Kalshi(
            api_key=os.getenv("KALSHI_API_KEY"),
            private_key=os.getenv("KALSHI_PRIVATE_KEY"),
        )
    elif name == "limitless":
        return pmxt.Limitless(
            api_key=os.getenv("LIMITLESS_API_KEY"),
            private_key=os.getenv("LIMITLESS_PRIVATE_KEY"),
        )
    elif name == "metaculus":
        return pmxt.Metaculus()
    elif name == "myriad":
        return pmxt.Myriad()
    elif name == "opinion":
        return pmxt.Opinion()
    elif name == "smarkets":
        return pmxt.Smarkets()
    else:
        # Try dynamic discovery
        cls = getattr(pmxt, name.capitalize(), None)
        if cls is None:
            raise ValueError(f"Unknown exchange: {name}")
        return cls()


def server_status() -> dict:
    """Get sidecar server status."""
    try:
        status = pmxt.server.status()
        # status is a dict, not an object
        if isinstance(status, dict):
            return {
                "running": status.get("running", False),
                "pid": status.get("pid"),
                "port": status.get("port"),
                "version": status.get("version"),
                "uptime_seconds": status.get("uptimeSeconds") or status.get("uptime_seconds"),
            }
        # Fallback for object-style
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
