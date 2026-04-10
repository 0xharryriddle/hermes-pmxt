# hermes-pmxt

Prediction market integration for [Hermes Agent](https://github.com/NousResearch/hermes-agent).
Search markets, check probabilities, detect arbitrage, and trade across Polymarket, Kalshi,
and Limitless — powered by [pmxt](https://github.com/pmxt-dev/pmxt).

## What This Is

A Hermes skill + Python toolset that gives any Hermes agent real-time access to prediction
markets. Instead of hallucinating probabilities, the agent checks actual market prices.

```
User: "Will Trump win 2028?"
Agent: *calls pmxt_search + pmxt_quote*
Agent: "The market implies a 1.9% chance (No: 98.1%). Polymarket is pricing this very low."
```

## Installation

```bash
# Clone
git clone https://github.com/0xharryriddle/hermes-pmxt.git
cd hermes-pmxt
```

### Option A: pip

```bash
# Create venv + install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Option B: uv

```bash
# Create venv + install
uv venv
source .venv/bin/activate
uv pip install -e .
```

```bash
# Install pmxt sidecar, pick one package manager
npm install -g pmxtjs
pnpm add -g pmxtjs
yarn global add pmxtjs
bun add -g pmxtjs
```

## Quick Start

```python
from hermes_pmxt import pmxt_search, pmxt_quote

# Search
result = pmxt_search("bitcoin", exchange="polymarket", limit=5)
for m in result["data"]:
    print(f"{m['title']}: YES={m['outcomes'][0]['price']*100:.1f}%")

# Quote, use a distinctive keyword or title phrase
quote = pmxt_quote("bitcoin reach", exchange="polymarket")
print(f"YES: {quote['data']['yes_pct']}  NO: {quote['data']['no_pct']}")
```

## Tools

| Function | Auth? | Description |
|----------|-------|-------------|
| `pmxt_search(query, exchange?, limit?)` | No | Search markets by keyword |
| `pmxt_quote(identifier, exchange)` | No | Get YES/NO probabilities from a keyword or title phrase |
| `pmxt_order_book(outcome_id, exchange)` | No | Get order book depth |
| `pmxt_ohlcv(outcome_id, exchange, resolution?, limit?)` | No | Get price candles |
| `pmxt_trades(outcome_id, exchange, limit?)` | No | Get recent trades |
| `pmxt_events(query, exchange?, limit?)` | No | Search events (groups of markets) |
| `pmxt_balance(exchange)` | Yes | Get account balance |
| `pmxt_positions(exchange)` | Yes | Get open positions |
| `pmxt_order(market_id, outcome, amount, side, exchange, price?)` | Yes | Place an order, `outcome` can be `yes`/`no`, a label, or an exact `outcome_id` |
| `pmxt_arbitrage_scan(query, exchanges?, threshold?)` | No | Cross-exchange spread scan |

## Hermes Skill

Copy `skill/SKILL.md` to `~/.hermes/skills/research/pmxt/SKILL.md` to give your
Hermes agent prediction market capabilities with behavior rules and safety guards.

For order placement, the safest flow is:
1. `pmxt_search(...)` or `pmxt_quote(...)` first, so the package caches the market's outcome IDs
2. `pmxt_order(...)` with `yes` / `no`, or pass the exact `outcome_id` directly

## Environment Variables

```bash
# Polymarket (trading only — read-only needs no keys)
export POLYMARKET_PRIVATE_KEY="0x..."
export POLYMARKET_PROXY_ADDRESS="0x..."  # Optional

# Kalshi
export KALSHI_API_KEY="..."
export KALSHI_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."

# Limitless
export LIMITLESS_API_KEY="..."
export LIMITLESS_PRIVATE_KEY="0x..."
```

## Project Structure

```
hermes-pmxt/
├── hermes_pmxt/
│   ├── __init__.py          # Public API exports
│   ├── tools.py             # Core tool functions
│   ├── exchanges.py         # Exchange initialization + caching
├── skill/
│   └── SKILL.md             # Hermes agent skill instructions
├── examples/
│   └── demo.py              # Interactive demo
├── tests/
│   ├── conftest.py          # Test import path setup
│   ├── test_tools.py        # Tool behavior tests
│   └── test_exchanges.py    # Exchange wiring tests
├── pyproject.toml
└── README.md
```

## Testing

```bash
# pip / existing venv
source .venv/bin/activate
pytest -q

# uv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pytest -q
```

## License

MIT
