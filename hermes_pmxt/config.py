"""
Runtime configuration and mode detection for hermes-pmxt.

Handles:
  - PMXT_API_KEY, PMXT_API_URL, PMXT_BASE_URL, PMXT_WALLET_ADDRESS, PMXT_PRIVATE_KEY
  - Hosted vs local sidecar vs custom server detection
  - Capability reporting

All functions work without pmxt installed.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Environment variable sources (ordered by precedence)
# ---------------------------------------------------------------------------

_HOSTED_URL = "https://api.pmxt.dev"
_TRADE_URL = "https://trade.pmxt.dev"
_LOCAL_URL = "http://localhost:3847"


def _get_api_key() -> Optional[str]:
    """Return the PMXT API key if configured."""
    return os.getenv("PMXT_API_KEY") or None


def _get_api_url() -> Optional[str]:
    """Return the explicit API URL override."""
    return os.getenv("PMXT_API_URL") or os.getenv("PMXT_BASE_URL") or None


def get_mode() -> str:
    """
    Detect the PMXT runtime mode.

    Returns one of:
      - 'hosted': PMXT_API_KEY is set, talks to api.pmxt.dev (or custom URL)
      - 'custom': PMXT_API_URL / PMXT_BASE_URL is set, custom server
      - 'local-sidecar': no key and no URL, assumes localhost:3847
      - 'unconfigured': not even local mode (no sidecar detectable)
    """
    key = _get_api_key()
    url = _get_api_url()

    if url:
        return "custom"
    if key:
        return "hosted"
    return "local-sidecar"


def get_base_url() -> str:
    """Return the base URL the SDK should use."""
    url = _get_api_url()
    if url:
        return url.rstrip("/")
    if _get_api_key():
        return _HOSTED_URL
    return _LOCAL_URL


def get_trade_url() -> str:
    """Return the hosted trade URL (for writes/account state)."""
    url = os.getenv("PMXT_TRADE_URL")
    if url:
        return url.rstrip("/")
    return _TRADE_URL


def get_wallet_address() -> Optional[str]:
    """Return the configured wallet address for hosted trading."""
    return os.getenv("PMXT_WALLET_ADDRESS") or None


def get_private_key() -> Optional[str]:
    """Return the configured private key for hosted trading."""
    return os.getenv("PMXT_PRIVATE_KEY") or None


# ---------------------------------------------------------------------------
# Runtime status
# ---------------------------------------------------------------------------


def runtime_status() -> dict:
    """
    Return a comprehensive runtime status dict.

    Works without pmxt installed. When pmxt is available, adds
    version, sidecar status, and exchange availability info.
    """
    result: dict = {
        "mode": get_mode(),
        "base_url": get_base_url(),
        "has_api_key": _get_api_key() is not None,
        "has_wallet_address": get_wallet_address() is not None,
        "has_private_key": get_private_key() is not None,
        "pmxt_installed": False,
        "pmxt_version": None,
        "python_version": sys.version,
    }

    try:
        from hermes_pmxt.exchanges import is_pmxt_available as _available

        if _available():
            import importlib.metadata as _metadata
            import pmxt  # type: ignore[import-untyped]

            result["pmxt_installed"] = True
            result["pmxt_version"] = getattr(pmxt, "__version__", None) or _metadata.version("pmxt")

            # Sidecar status (best effort)
            try:
                s = pmxt.server.status()
                if isinstance(s, dict):
                    result["sidecar_running"] = s.get("running", False)
                    result["sidecar_port"] = s.get("port")
                    result["sidecar_pid"] = s.get("pid")
            except Exception:
                result["sidecar_running"] = False
    except ImportError:
        pass

    return result


def runtime_status_str() -> str:
    """Return a human-readable one-liner of runtime status."""
    status = runtime_status()
    parts = [f"mode={status['mode']}", f"url={status['base_url']}"]
    if status["pmxt_installed"]:
        parts.append(f"pmxt={status['pmxt_version'] or '?'}")
        if status.get("sidecar_running"):
            parts.append(f"sidecar=:{status.get('sidecar_port','?')}")
        else:
            parts.append("sidecar=off")
    else:
        parts.append("pmxt=not_installed")
    return " ".join(parts)
