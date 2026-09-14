# Native Hermes integration: design research

Status: proposal, not implemented. Complements hermes-compatibility-release.md.

## Product boundary

Ship one distribution with three layers:

1. SDK: existing public Python functions, no Hermes dependency.
2. Native adapter: register(ctx), explicit schemas and handlers, installed through
   a hermes_agent.plugins entry point. No host-registry imports or monkeypatches.
3. Bundled skill: workflow instructions registered using ctx.register_skill,
   resolved from package resources rather than the working directory.

Preserve existing import paths where behavior can remain correct. Document any
changed response contract. Native adapter serializes SDK results as JSON strings
and accepts host-added handler kwargs without forwarding them to the venue SDK.

## Native versus MCP

Prefer the native adapter for the maintained hermes-pmxt experience: curated tool
schemas, compact outputs, diagnostics, and an integrated skill. PMXT's upstream
MCP is a useful alternative, not a second execution route silently enabled by the
plugin. Do not register both surfaces by default: duplicated tools, credentials,
and conflicting safety policy would make behavior harder to understand.

## Initial model-facing surface

Proposed groups, subject to the upstream API audit:
- Diagnostics: runtime status and per-mode venue capabilities.
- Discovery: events, markets, exact lookup, series where supported.
- Research: quote, book, history, recent trades.
- Router: matched clusters and price comparison with relation/confidence evidence.
- Portfolio: explicit opt-in authenticated reads; no auto-discovery of wallets.
- Execution planning: estimates and unsigned intent previews.

Avoid exposing every upstream method as a separate model tool. Keep explicit
schemas for common tasks; a generic call must have a reviewed allowlist and must
not bypass write restrictions through aliases or fallback dispatch.

## Trading boundary

Read-only is the default. Registration, diagnostics, and skill discovery must not
start servers, sign payloads, move assets, or call external services.

The documented ctx.register_approval_transport API only routes existing host
approval requests. It is NOT an authorization-policy API or proof that arbitrary
financial tool calls receive human approval. Do not invent a ctx approval method.

Until an appropriate authorization path is verified, keep native trade submission,
cancellation, withdrawals, and funding disabled. Preserve any SDK write APIs only
with explicit documentation of their caller-controlled authorization boundary.

A later native trading feature needs request-bound approval of exact exchange,
account, market/outcome IDs, side, size/denomination, limit/slippage and expiration;
replay prevention; and an unknown-outcome reconciliation path instead of blind
retry after timeouts. Building/signing is not automatically a harmless preview.

## Packaging and installation

- Entry point target proposed: hermes_pmxt.plugin:register.
- Bundle skill under package data; one canonical source, no independently edited
  README/skill copies with conflicting contracts.
- Native adapter has no import-time dependency on Hermes internals.
- Do not enable installed plugins automatically or edit user config during pip
  installation. Explain explicit enable and session restart.
- Use the Python interpreter that runs Hermes. A pip install into an unrelated
  environment does not make a plugin discoverable by the host.
- Directory-plugin support is optional; if provided, test it separately and avoid
  duplicate pip/directory registration. Do not claim it works merely because the
  pip route does.

## Acceptance gates

- Isolated wheel installation outside checkout; assert module origin and skill
  resource existence from installed distribution.
- Real PluginManager entry-point discovery and enabled/disabled behavior under
  isolated HERMES_HOME; assert tool and skill registration.
- Invoke registered handlers through the actual host dispatcher with controlled
  provider responses. Assert schemas, JSON output, invalid arguments and errors.
- Registration under network-denial test; zero backend calls.
- No credentials in outputs, diagnostics, logs or package resources.
- Upstream compat scanner with nonempty manifest and positive control.
- hermes plugins doctor --ci where the selected packaging route is supported;
  do not treat a directory-only doctor result as pip-entry-point coverage.
- Native read-only smoke against a real backend is a separate gate from mocked
  dispatch. No live trading in CI.

## Primary sources checked

- https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/
- https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins
- https://github.com/NousResearch/hermes-agent/blob/main/COMPAT_MANIFEST.md
- https://pmxt.dev/docs (Router and hosted/self-hosted overview)

The plugin documentation explicitly provides register_tool, register_skill,
pip entry points, and opt-in enablement. It also explicitly distinguishes approval
transport from authorization policy. Internal imports remain unstable.
