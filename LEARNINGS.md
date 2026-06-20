# Learnings -- Building hermes-pmxt v0.3.0

Things discovered during upgrade that differ from docs/research.

## pmxt SDK Realities (v2.50.x)

### Version metadata is inconsistent across sources
- PyPI: `pmxt 2.50.16`
- Raw Python pyproject.toml in monorepo: `2.18.0`
- monorepo package.json: `pmxtjs ^2.17.1`
- Generated pmxt-mcp tools.ts: `2.50.16` (2026-06-18)
- **Lesson**: Rely on runtime capability detection, not version strings.

### Dual API hosts
- `api.pmxt.dev` - reads, Router, MCP, venue passthrough
- `trade.pmxt.dev` - hosted writes + hosted account state
- Both authenticate with the same `pmxt_api_key`.

### Python SDK has hosted mode built-in
- `Exchange.__init__()` accepts `pmxt_api_key`, `wallet_address`, `base_url`
- Auto-resolves base URL: `PMXT_BASE_URL` → `pmxt_api_key` presence → localhost
- `build_order` + `submit_order` exist natively in Python SDK >= 2.50
- `call_api(operation_id, params)` exposes raw OpenAPI endpoints

### Router is NOT a separate Python class
- Router appears as `exchange="router"` target
- Router methods: `compareMarketPrices`, `fetchMarketMatches`, `fetchArbitrage`, etc.
- Available via `pmxt_call("methodName", "router", params={...})`

### server.status() returns a dict, not an object
- Keys: `running`, `pid`, `port`, `version`, `uptime_seconds`, `lock_file`
- Must use `.get()` not attribute access.

### fetch_market() (singular) doesn't work by ID
- `exchange.fetch_market(market_id="701486")` throws `PmxtError: Unknown error`
- **Workaround**: Use `fetch_markets(query=keyword, limit=N)`.

### outcome_id is Very Long
- Polymarket outcome_ids are 70+ character token IDs
- Use labels for display, pass IDs as-is for API calls

## pmxt-mcp Design Patterns Worth Adopting

### Auto-generated tool surface
- PMXT-MCP generates `src/generated/tools.ts` from OpenAPI + method-verbs.json
- Auto-runs on every PMXT release via GitHub Actions `sync-mcp.yml`
- hermes-pmxt should adopt: `scripts/sync_pmxt_registry.py`

### Flat agent-friendly schemas
- Complex params flattened to top-level MCP tool inputs
- `ArgSpec` metadata for runtime positional reconstruction
- `flatten: true` flags merged params for cleaner agent UX

### Safety annotations built into tools
- `readOnlyHint: true` - safe for repeated calls
- `destructiveHint: true` - requires confirmation
- `idempotentHint: true` - safe to retry
- hermes-pmxt mirrors this in registry.py

### Three config modes: hosted / local / custom
- `PMXT_API_URL` overrides everything
- `PMXT_API_KEY` → hosted `api.pmxt.dev`
- Neither → local `http://localhost:3847`
- hermes-pmxt mirrors this in config.py

### Compact result shaping
- `verbose=false` (default): compact agent-friendly output
- `verbose=true`: raw uncompacted
- Strips market status when active, truncates descriptions
- hermes-pmxt mirrors this in shaper.py

### Instructions favor events first
- pmxt-mcp tells agents: "users say 'market', they mean 'event'"
- Discovery: fetchEvents → drill to markets → outcomes

## Price Scale
All prices confirmed as 0.0-1.0 (probabilities). Kalshi internally uses 0-100
but pmxt normalizes to 0-1 in the Python SDK.

## Trade Timestamps
All timestamps are Unix milliseconds. Divide by 1000 for Python datetime.

## Kalshi Behavior
- Returns markets with `before`/`not before` label style
- Read-only without API keys (local sidecar mode)
- Search is slower than Polymarket

## hermes-pmxt Architecture Decisions (v0.3.0)

### Lazy import over eager import
- `exchanges.py` uses `_get_pmxt()` lazy getter
- Package imports cleanly without pmxt installed
- Only raises ImportError when pmxt functionality is used

### Generated registry over manual wrappers
- `registry.py` has ~33 tool definitions with safety annotations
- `pmxt_call()` dispatches to SDK methods with guard rails
- Handwritten wrappers for common flows only

### confirmed=True gate for destructive ops
- `createOrder`, `submitOrder`, `cancelOrder` require `confirmed=True`
- `_require_confirmed()` returns human-readable error when not confirmed

### Runtime status as first troubleshooting step
- `pmxt_runtime_status()` shows mode, URL, version, sidecar health
- Works without pmxt installed

### Exchange list with capability detection
- 17 known exchanges in registry
- `pmxt_list_exchanges()` reports which are available in installed build
- Aliases for common naming variants
