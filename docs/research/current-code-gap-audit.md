# Current-code gap audit against PMXT 2.54.0

Scope: read-only source + direct inspection of a clean `pmxt==2.54.0` wheel.
No wallet, sidecar, live market, order, cancellation, or credentialed API call ran.

## P0 correctness blockers

| Location | Evidence | Required change |
|---|---|---|
| `hermes_pmxt/exchanges.py:89-100` | `_ensure()` users call `ensure_server()`, which always checks/starts a local sidecar. Hosted PMXT clients are therefore forced through a local-server prerequisite despite `config.py` recognizing `PMXT_API_KEY`. | Make readiness mode-aware: hosted uses no sidecar; custom/local use an explicit health probe/start policy. Never start a process in plugin registration. |
| `hermes_pmxt/exchanges.py:126-154` | Constructors receive venue-native values but never receive `pmxt_api_key`, `wallet_address`, global private key or configured base URL. Generic class naming maps `polymarket_us` to `PolymarketUs`, while wheel exports `PolymarketUS`/`Polymarket_us`. | Add explicit class map and a centralized constructor-kwargs builder per mode. Require test coverage for hosted, custom, and self-hosted arguments. |
| `hermes_pmxt/tools.py:1185-1242` | `pmxt_call()` passes `params` as one positional argument. PMXT Router 2.54 methods use keyword-only selectors (e.g. market_id/slug/query). | Reconstruct args/kwargs from registry specs or remove generic call from model/native surface. Validate direct client signatures. |
| `hermes_pmxt/tools.py:759-769` | `pmxt_order()` sends `type`; PMXT 2.54 `create_order()` accepts keyword-only `order_type`. | Correct only if retaining legacy SDK write path; native plugin must not register it in 0.4.0. Add fail-closed unit test. |
| `hermes_pmxt/tools.py:1313-1342, 1347-1376` | `pmxt_build_order()` returns a summary dict but `pmxt_submit_order()` passes a dict to SDK. PMXT 2.54 requires `BuiltOrder`. The actual signed object is discarded. | Do not expose this pair as a working workflow. Either retain a validated opaque server-side intent handle with request binding or quarantine/remove it pending a design for authenticated human approval. |

## P1 product/API drift

| Location | Evidence | Required change |
|---|---|---|
| `hermes_pmxt/registry.py:77-99, 122-214` | Snapshot says 2.50.x; lacks Hunch and 2.54 Router methods. It treats 17 keys including mock/router as venues. | Generate/validate registry; separate real venues, virtual Router, mock/testing and mode-specific capabilities. |
| `hermes_pmxt/exchanges.py:44-60` | Only eight venues and a broad fixed trading tuple. PMXT upstream has 16 real venue targets; Hunch does not support generic limit/sell/cancel flow. | Derive presentation from safe static metadata plus explicit capability probe. |
| `hermes_pmxt/shaper.py:25-93, 194-255` | Shaper only meaningfully compacts dicts. PMXT Python API returns model objects. Market fields omit outcome IDs in list results, and comparison is YES/NO-shaped. | Add a tested model-to-plain-data boundary, preserve N-way outcome IDs and outcome labels, add series/cluster shapes. |
| `hermes_pmxt/tools.py:915-1115` | Cross-venue comparison and arbitrage use title overlap. Output says `risk-free profit`, but correlation of titles does not establish identical rules, execution/fee capacity, or settlement compatibility. | Prefer Router matches/clusters and relation/confidence. Rename output to review candidate; expose source/provenance and state limitations. |
| `hermes_pmxt/config.py:115-116` | Version field prefers `pmxt.__version__`. Upstream source checkout exposes stale 2.17.x while PyPI wheel is 2.54.0. | Prefer installed distribution metadata; report package source/version discrepancy only as diagnostic. |

## Test/CI blockers

- `.github/workflows/workflow.yml:40-41` runs `-m unit` only. Offline
  `not integration and not trading` collection contains 42 tests while unit
  collection contains 32. Ten exchange tests are not executed in CI.
- No installed-wheel test checks the module origin outside repo cwd.
- No PMXT 2.54 signature/model contract test.
- No native PluginManager integration test; project currently has no plugin entry
  point or `register(ctx)` implementation.
- Existing unit tests have no live sidecar/backend dependence, which is correct for
  CI but insufficient to verify hosted/self-hosted contract selection.

## Release implication

0.4.0 is blocked by the P0 items. It must be a read-only native-plugin release.
Do not call the current build/submit flow safe or fully supported until its object
lifecycle and host-level human authorization have been designed and tested.
