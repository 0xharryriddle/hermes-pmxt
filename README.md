# hermes-pmxt

Prediction-market research integration for [Hermes Agent](https://github.com/NousResearch/hermes-agent),
powered by [PMXT](https://github.com/pmxt-dev/pmxt) 2.54.x.

## What This Is

A Python SDK, native Hermes plugin, and bundled skill for real-time prediction-market research.
The native plugin is read-only: it discovers events/markets, examines series and order books,
and uses PMXT Router relation/confidence evidence for cross-venue research.

```
User: "Will Trump win 2028?"
Agent: *calls pmxt_search + pmxt_quote*
Agent: "The market implies a 1.9% chance (No: 98.1%). Polymarket is pricing this very low."
```

## Installation

The PyPI package is live. For most users, this is the whole install:

```bash
pip install hermes-pmxt
```

Verify it works:

```bash
python3 -c "from hermes_pmxt import pmxt_runtime_status; print(pmxt_runtime_status())"
```

### Native Hermes Plugin

Install into the same Python environment that runs `hermes`, then explicitly enable it:

```bash
python -m pip install hermes-pmxt
hermes plugins enable hermes-pmxt
```

Restart Hermes or begin a new session after enabling. The plugin bundles a namespaced skill
available as `hermes-pmxt:pmxt`. It exposes only read-only tools:

```text
pmxt_runtime_status, pmxt_list_exchanges, pmxt_search, pmxt_events,
pmxt_series, pmxt_order_books, pmxt_matched_market_clusters
```

The plugin does not submit orders, cancel orders, fund accounts, or access wallet operations.
The Python SDK retains its separately documented, confirmation-gated legacy order helpers.

### Upgrade

```bash
pip install --upgrade hermes-pmxt
```

### Development Install

Only clone the repo if you are modifying hermes-pmxt itself:

```bash
git clone https://github.com/0xharryriddle/hermes-pmxt.git
cd hermes-pmxt
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Modes

hermes-pmxt supports three runtime modes:

| Mode | Config | Behavior |
|------|--------|----------|
| **Hosted** | Set `PMXT_API_KEY` | Talks to `https://api.pmxt.dev`. Handles exchange connections, caching, and rate limits automatically. Recommended for most users. |
| **Custom** | Set `PMXT_API_URL` or `PMXT_BASE_URL` | Points to any PMXT-compatible server. |
| **Local Sidecar** | No API key/URL set | Assumes PMXT core is running at `http://localhost:3847`. For self-hosting / development. |

Check your current mode:
```python
from hermes_pmxt import pmxt_runtime_status
print(pmxt_runtime_status())
```

## Quick Start

```python
from hermes_pmxt import pmxt_search, pmxt_quote, pmxt_runtime_status

# Check status
print(pmxt_runtime_status())

# Search
result = pmxt_search("bitcoin", exchange="polymarket", limit=5)
for m in result["data"]:
    prices = m.get("outcomes", [])
    if prices:
        print(f"{m['title'][:60]}: YES={prices[0]['price']*100:.1f}%")

# Quote
quote = pmxt_quote("bitcoin reach", exchange="polymarket")
print(f"YES: {quote['data']['yes_pct']}  NO: {quote['data']['no_pct']}")
```

## Data Model

```
  Event (broad topic)
    └── Market (tradeable question)
          └── Outcome (one or more labelled positions)
```

When users ask about a topic, start with events (`pmxt_events`), then drill down to
markets and outcomes.

## Tools

### Discovery & Research

| Function | Auth | Description |
|----------|------|-------------|
| `pmxt_search(query, exchange?, limit?, sort?, search_in?, slug?)` | No* | Search markets by keyword |
| `pmxt_events(query, exchange?, limit?, sort?, search_in?, slug?)` | No* | Search event groups |
| `pmxt_quote(identifier, exchange)` | No* | Get YES/NO probabilities |
| `pmxt_order_book(outcome_id, exchange, limit?)` | No* | Order book depth |
| `pmxt_ohlcv(outcome_id, exchange, resolution?, limit?)` | No* | Price candles |
| `pmxt_trades(outcome_id, exchange, limit?)` | No* | Recent trades |
| `pmxt_execution_price(outcome_id, exchange, side, amount)` | No* | Slippage estimate |
| `pmxt_call("fetchSeries", exchange, ...)` | No* | Venue-native series |
| `pmxt_call("fetchOrderBooks", exchange, ...)` | No* | Batch order books |

### Cross-Venue & Arbitrage

| Function | Auth | Description |
|----------|------|-------------|
| `pmxt_compare_market(query, exchanges?, limit?)` | No* | Compare prices across exchanges |
| `pmxt_arbitrage_scan(query, exchanges?, threshold?)` | No* | Detect arbitrage opportunities |
| `pmxt_call("compareMarketPrices", "router", ...)` | No* | Native router comparison |
| `pmxt_call("fetchMatchedMarketClusters", "router", ...)` | No* | Cross-venue matches with relation/confidence evidence |
| `pmxt_call("fetchArbitrage", "router", ...)` | No* | Native arbitrage candidates for review |
| `pmxt_call("fetchHedges", "router", ...)` | No* | Hedging opportunities |

### Portfolio & Account

| Function | Auth | Description |
|----------|------|-------------|
| `pmxt_balance(exchange)` | Yes | Account balance |
| `pmxt_positions(exchange)` | Yes | Open positions |
| `pmxt_portfolio(exchanges?)` | Yes | Cross-exchange portfolio |

### Trading (All Destructive -- Require Explicit Confirmation)

| Function | Auth | Description |
|----------|------|-------------|
| `pmxt_build_order(...)` | Yes | Build/sign order without submitting (SAFE) |
| `pmxt_submit_order(built, exchange, confirmed=True)` | Yes | Submit a pre-built order |
| `pmxt_cancel_order(order_id, exchange, confirmed=True)` | Yes | Cancel an open order |
| `pmxt_order(...)` | Yes | Legacy one-step order (prefer build+submit) |

### Generic API Call

| Function | Auth | Description |
|----------|------|-------------|
| `pmxt_call(method, exchange, ...)` | Varies | Generic PMXT API call with safety checks |

### Server & Diagnostics

| Function | Auth | Description |
|----------|------|-------------|
| `pmxt_runtime_status()` | No | Full runtime status |
| `pmxt_list_exchanges()` | No | Known/available exchanges |
| `pmxt_server_status()` | No | Sidecar diagnostics |
| `pmxt_server_start()` | No | Start sidecar |
| `pmxt_server_stop()` | No | Stop sidecar |

\* Read-only tools work without credentials in local sidecar mode. Hosted mode requires `PMXT_API_KEY` for all operations.

## Trading Safety

**Destructive operations (create, submit, cancel orders) require explicit user confirmation.**

```python
# SAFE: Build order for preview (does NOT place a real order)
preview = pmxt_build_order(
    market_id="market-uuid",
    outcome="yes",
    side="buy",
    order_type="limit",
    amount=10,
    price=0.55,
    exchange="polymarket",
)

# DESTRUCTIVE: Submit the one-time token after explicit user confirmation.
result = pmxt_submit_order(preview["data"]["submission_token"], "polymarket", confirmed=True)

# Caller-built dicts are rejected; the SDK BuiltOrder remains process-local.
# A token is one-time use and bound to the exchange used for build.
```

## Supported Exchanges

hermes-pmxt knows about PMXT's current venue targets plus `router` and `mock`, including:

- `polymarket` / `polymarket_us`
- `kalshi` / `kalshi-demo`
- `limitless`
- `probable` / `baozi` / `myriad` / `opinion`
- `metaculus` / `smarkets`
- `gemini-titan` / `hyperliquid` / `suibets` / `rain` / `hunch`
- `mock` / `router`

Actual availability depends on the installed `pmxt` build. Run `pmxt_list_exchanges()` to check.

## Environment Variables

```bash
# Hosted mode (recommended)
export PMXT_API_KEY="pmxt_live_..."
export PMXT_WALLET_ADDRESS="0x..."
export PMXT_PRIVATE_KEY="0x..."

# Custom server
export PMXT_API_URL="https://your-server.com"
# or
export PMXT_BASE_URL="https://your-server.com"

# Venue-specific (self-hosted mode)
export POLYMARKET_PRIVATE_KEY="0x..."
export POLYMARKET_PROXY_ADDRESS="0x..."  # Optional
export KALSHI_API_KEY="..."
export KALSHI_PRIVATE_KEY="..."
export LIMITLESS_API_KEY="..."
export LIMITLESS_PRIVATE_KEY="..."
export POLYMARKET_US_API_KEY="..."
export POLYMARKET_US_PRIVATE_KEY="..."
```

## Project Structure

```
hermes-pmxt/
├── hermes_pmxt/
│   ├── __init__.py          # Public API exports
│   ├── config.py            # Runtime config and mode detection
│   ├── exchanges.py         # Exchange initialization + normalization
│   ├── registry.py          # Tool registry with safety annotations
│   ├── shaper.py            # Result shaping for LLM context
│   └── tools.py             # Core tool functions
├── skill/
│   └── SKILL.md             # Hermes agent skill instructions
├── examples/
│   └── demo.py              # Interactive demo
├── tests/
│   ├── conftest.py          # Test path setup
│   ├── test_exchanges.py    # Exchange wiring unit tests
│   └── test_tools.py        # Unit + integration tests
├── pyproject.toml
└── README.md
```

## Testing

```bash
# Unit tests (no pmxt required)
python3 -m pytest -q -m unit

# All non-destructive tests
python3 -m pytest -q -m "not trading"

# Integration tests (need pmxt + sidecar/API)
python3 -m pytest -q -m integration
```

## License

MIT
