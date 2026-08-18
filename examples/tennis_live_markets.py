#!/usr/bin/env python3
"""
hermes-pmxt tennis example -- ground market quotes in live match state.

The agent pitch of hermes-pmxt is "check actual market prices instead of
hallucinating probabilities". For in-play sports markets the same argument
applies to the event itself: don't reason about a tennis market without
knowing the actual score. This example searches tennis markets via pmxt,
then pairs each market with the live match state (score, server, status)
from the Live Tennis API before any quote is interpreted.

Disclosure: this example was contributed by the Live Tennis API team
(https://livetennisapi.com). The live-state lookup uses their free keyed
tier (30 requests/minute, 100 requests/day -- fine for developing and
testing or ~15-minute checks, NOT continuous in-play polling; sustained
live use needs a paid tier). Free key: https://livetennisapi.com/subscribe/free

Usage:
    source .venv/bin/activate
    export LIVETENNIS_API_KEY=...   # optional; the example degrades gracefully
    python examples/tennis_live_markets.py
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# Add parent to path so we can import hermes_pmxt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes_pmxt import pmxt_quote, pmxt_search

LIVETENNIS_BASE_URL = "https://api.livetennisapi.com/api/public/v1"


def pp(label: str, result: dict):
    """Pretty-print a tool result (same shape as examples/demo.py)."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    if not result["success"]:
        print(f"  ERROR: {result.get('error', 'unknown')}")
        return None

    data = result["data"]
    if isinstance(data, list):
        print(f"  {len(data)} items")
        for i, item in enumerate(data[:5]):
            title = item.get("title", str(item)[:60]) if isinstance(item, dict) else item
            print(f"    [{i}] {title}")
        if len(data) > 5:
            print(f"    ... and {len(data) - 5} more")
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (list, dict)) and len(str(v)) > 100:
                print(f"  {k}: [{len(v)} items]" if isinstance(v, list) else f"  {k}: {{...}}")
            else:
                print(f"  {k}: {v}")
    else:
        print(f"  {data}")
    return data


def fetch_live_tennis_matches() -> list[dict]:
    """Fetch matches in progress from the Live Tennis API free tier.

    Returns [] (with a note) when LIVETENNIS_API_KEY is unset, so the
    example still demonstrates the market half without a key.
    """
    api_key = os.environ.get("LIVETENNIS_API_KEY")
    if not api_key:
        print("\n  LIVETENNIS_API_KEY not set -- skipping live match state.")
        print("  Free key: https://livetennisapi.com/subscribe/free")
        return []

    url = LIVETENNIS_BASE_URL + "/matches?" + urllib.parse.urlencode(
        {"status": "live", "limit": 50}
    )
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            print("  Rate limit hit (free tier: 30 req/min, 100 req/day). Slow down.")
            return []
        raise
    return payload.get("data", []) if isinstance(payload, dict) else []


def surnames(title: str) -> set[str]:
    """Lowercased surname-ish tokens from a market title or player name."""
    tokens = re.split(r"[^a-zA-Z]+", title.lower())
    return {t for t in tokens if len(t) >= 4}


def match_market_to_live(title: str, live_matches: list[dict]) -> dict | None:
    """Pair a market title with a live match by shared player surnames."""
    market_tokens = surnames(title)
    for match in live_matches:
        players = f"{match.get('player1_name', '')} {match.get('player2_name', '')}"
        if len(market_tokens & surnames(players)) >= 2:
            return match
    return None


def score_line(score: dict | None) -> str:
    """Render '6-4 3-2 (40-15)' from a Live Tennis API score object."""
    if not score:
        return "(no score data)"
    parts = []
    games = score.get("games") or []
    if len(games) == 2 and games[0] and len(games[0]) == len(games[1]):
        parts = [f"{a}-{b}" for a, b in zip(games[0], games[1])]
    points = score.get("points") or []
    if len(points) == 2 and points[0] is not None and points[1] is not None:
        parts.append(f"({points[0]}-{points[1]})")
    return " ".join(parts) or "(no score data)"


def main():
    print("hermes-pmxt tennis example")
    print("=" * 60)

    # 1. Search tennis markets on Polymarket
    markets = pp(
        "Search: 'tennis' on Polymarket",
        pmxt_search("tennis", exchange="polymarket", limit=10),
    )
    if not markets:
        print("\nNo tennis markets found right now (try during a tournament). Exiting.")
        return

    # 2. Live match state from the Live Tennis API (free keyed tier)
    live_matches = fetch_live_tennis_matches()
    print(f"\n  Live tennis matches right now: {len(live_matches)}")

    # 3. Quote each market NEXT TO the actual state of its match
    for market in markets[:5]:
        title = market["title"]
        keyword = title[:40]
        quote = pmxt_quote(keyword, "polymarket")
        live = match_market_to_live(title, live_matches)

        print(f"\n{'-' * 60}")
        print(f"  Market: {title}")
        if quote["success"] and isinstance(quote["data"], dict):
            for k in ("bid", "ask", "last", "mid"):
                if k in quote["data"]:
                    print(f"    {k}: {quote['data'][k]}")
        if live is None:
            print("    Live state: not in progress (or no key set)")
            continue
        score = live.get("score") or {}
        server = score.get("server")
        serving = (
            live.get(f"player{server}_name") if server in (1, 2) else "unknown"
        )
        print(f"    Live state: {live.get('player1_name')} vs {live.get('player2_name')}")
        print(f"      score:   {score_line(score)}")
        print(f"      serving: {serving}")
        print(f"      status:  {live.get('event_status') or live.get('status')}")

    print(f"\n{'=' * 60}")
    print("  Done. Quotes without event state are only half the picture.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
