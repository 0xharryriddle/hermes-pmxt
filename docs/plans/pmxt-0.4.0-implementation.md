# 0.4.0 implementation plan: PMXT 2.54 + Hermes native plugin

Status: proposal backed by direct 2.54.0 wheel inspection and current-code audit.
Execution requires no real-money credentials. Release/publish remains owner-gated.

## Decision

Ship a read-only native Hermes plugin in 0.4.0, with the existing Python SDK kept
as the programmatic surface. SDK trading wrappers remain backward-compatible but
are excluded from the native plugin. The native plugin has no generic raw-call
tool: opaque method dispatch would erase the safety and schema boundary.

## Milestone 1 — SDK contract hardening

1. `pyproject.toml`
   - Change PMXT requirement to a qualified 2.54 series, after tests pin actual
     wheel behavior.
   - Add explicit runtime entry point for the plugin only when adapter tests pass.
   - Package the canonical skill and required metadata as wheel data.

2. `exchanges.py`
   - Add current known venues including Hunch and Router.
   - Split known venue names from *available* classes and from *capability-probed*
     venues. Do not read `.has` during import, list rendering or registration:
     PMXT 2.54 performs an HTTP request for it.
   - Construct hosted clients with PMXT_API_KEY / wallet data correctly and use a
     dedicated Router constructor. Preserve no-network construction behavior.
   - Replace optimistic `TRADING_EXCHANGES` tuple with capability/mode-aware
     reporting. Hunch read-only hosted must never be advertised as standard
     cancellable limit-order trading.

3. `registry.py`
   - Replace hand-maintained claims with a generated/validated snapshot sourced
     from the PMXT method manifest.
   - Divide methods: curated native read-only, SDK-only read-only, SDK write,
     websocket/session lifecycle. Mark build/sign as sensitive, not read-only.
   - Add `fetchSeries`, `fetchOrderBooks`, Router cluster methods. Do not expose
     auth/session/watch methods from native plugin v1.

4. `tools.py` + `shaper.py`
   - Add dedicated wrappers for series, batch books and Router matched clusters.
   - Pass kwargs to current PMXT signatures; current `pmxt_call` incorrectly turns
     flat params into a positional dict for methods whose client API is keyword
     based (notably Router compare/match operations).
   - Serialize PMXT dataclass/Pydantic models before shaping. Current shaper only
     compacts dicts; direct SDK lists/models bypass meaningful compaction.
   - Preserve N-way outcome IDs, labels and prices; remove binary-only assumptions
     from native discovery/comparison tools.
   - Retire heuristic title-overlap arbitrage from native surface. It cannot prove
     identical settlement conditions, fees, execution capacity or transfer
     feasibility. Use PMXT Router relation/confidence evidence and describe it as
     an opportunity for review, never risk-free profit.
   - Return structured errors with operation/exchange/error-type but no secrets.

## Milestone 2 — native Hermes plugin

5. New package boundary
   - `hermes_pmxt/plugin.py`: top-level `register(ctx)`, small/no side effects.
   - `hermes_pmxt/plugin_schemas.py`: static JSON schemas.
   - `hermes_pmxt/plugin_handlers.py`: transforms tool args to SDK calls and JSON
     serializes standard response envelopes. Accept `**kwargs` from host.
   - `hermes_pmxt/skill/SKILL.md`: canonical bundled skill resource.
   - Register namespaced skill via `ctx.register_skill("pmxt", resource_path)`.
   - Register curated read-only tools under `pmxt_*` names. Use stable documented
     PluginContext only; no Hermes internal import.

6. Install/config UX
   - Document installing into Hermes' own Python environment, then explicit
     `hermes plugins enable hermes-pmxt`; restart/new session required.
   - Add configuration schema only for harmless endpoint/timeouts/default venue.
   - PMXT API key is optional: hosted mode with a key; self-hosted requires an
     accessible sidecar. Never put credentials into plugin manifests or logs.

## Milestone 3 — test and quality gates

7. Unit and contract tests
   - Add marker discipline: CI runs all offline, non-trading tests; collection
     assertion blocks unmarked offline test omissions.
   - Fixture models for binary, N-way, Hunch, Router match/cluster, paginated
     results and typed PMXT errors.
   - Pin tests against 2.54.0 actual signatures; run a bounded compatibility
     matrix after that.

8. Plugin harness
   - Isolated HERMES_HOME, actual entry-point discovery, enable/disable, doctor,
     tool and skill registration through PluginManager.
   - Network-denied registration test. Direct handler tests with mocked adapter.
   - Wheel install outside checkout; assert import origin, entry-point metadata
     and bundled skill resource. Do not let cwd shadow the installed wheel.

9. Integration/release
   - Opt-in read-only hosted/self-hosted smoke with exact value/ID assertions;
     no funds, orders, cancels or wallet keys in CI.
   - Run current Hermes compat scanner with positive control.
   - Lint, full offline suite, build, twine, wheel smoke, plugin harness.
   - Bump 0.4.0 only after all gates pass. PyPI publish requires explicit owner
     approval; upload once through main-only OIDC and read back installed version.

## Sequencing

Start Milestone 1 with serialization, exchange/config separation and tests. Next
land Plugin boundary with read-only tools and harness. Last, docs/CI/version and
release qualification. Do not start live trading implementation in this release.
