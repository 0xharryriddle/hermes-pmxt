# Hermes compatibility assessment and release plan

## Scope and decision

Research only; no release or runtime migration performed. Repository inspected at
`fdeca2e398ec8aacca92b6723b78e4ef84e1c437`. PyPI currently reports 0.3.0.

The current project is a Python SDK plus a Markdown skill, not a native Hermes
plugin: no plugin manifest, `hermes_agent.plugins` entry point, or `register(ctx)`
adapter is shipped. Runtime modules import stdlib, pmxt, and hermes_pmxt, not Hermes
internal modules. No old-to-new import substitutions are required for this revision.

Recommend 0.3.1 for compatibility documentation, installation corrections, and
regression coverage. Do not label it an emergency import migration. Reserve 0.4.0
for an optional native plugin, requiring a separate implementation decision.

## Upstream findings

- PR #102117 merged on 2026-09-04, merge commit
  `d3630f853239e8c41ce7201e09fbdf39bcbc5431`.
- Temporary internal-import compatibility pointers are scheduled for removal on
  2026-09-14. Affected plugins are disabled from that date; unaffected plugins are
  not subject to a blanket migration.
- `plugins.allow_deprecated_imports: true` is only a temporary escape hatch before
  pointers disappear; it is not a migration strategy.
- Private names are not generally restored. Renaming imports alone is not enough
  for plugins that monkeypatch private implementation details.
- Documented PluginContext behavior is distinct from unstable internal imports.
  Prefer `register(ctx)` and documented context methods when adding integration.

Sources:
- https://github.com/NousResearch/hermes-agent/blob/main/COMPAT_MANIFEST.md
- https://github.com/NousResearch/hermes-agent/pull/102117
- https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/

## Evidence and limits

- Installed CLI: Hermes v0.21.1 (2026.9.7), upstream 3868ee9a as reported by CLI.
  This is the installed build, not proof it equals current upstream main.
- `hermes plugins compat <repository> --json`: removal date 2026-09-14,
  `in_effect: false`, `plugins: {}`.
- Inspected scanner implementation. Loaded manifest contains 335 module entries.
  Positive control `from agent.anthropic_adapter import get_hermes_home` produces
  a finding pointing to `hermes_constants.get_hermes_home`. Repository scan returns
  zero findings. Thus the scanner runs; this is not a native-plugin loading test.
- Independent AST inventory of runtime imports finds no Hermes internal imports.
- `python3 -m pytest -q -m 'not integration and not trading'`: 42 passed,
  12 deselected. Live market access and real-money execution were not tested.
- The historical claim that a local-checkout import verifies a PyPI installation
  is insufficient: cwd can shadow site-packages. Future wheel tests must run
  outside the checkout and assert the imported module's installed location.

## Proposed 0.3.1 work

1. Installation and documentation
   - Describe SDK + skill accurately; remove generic native-plugin installation
     advice until a real plugin is shipped.
   - Use interpreter-qualified pip commands and explain installing into the
     interpreter used by Hermes execution, respecting the active profile.
   - Distinguish successful diagnostics from a healthy backend and a successful
     live market query. Keep documentation concise.
   - Document migration applicability and scan command without claiming universal
     Hermes compatibility from zero scanner hits.

2. Regression and package qualification
   - Add an independence test that rejects imports of Hermes runtime internals;
     include a positive-control fixture and fail on parse errors.
   - Test pmxt missing and present explicitly, not environment-dependent booleans.
   - Build wheel/sdist; install the wheel in an isolated environment. Run outside
     the checkout, verify module origin, imports, diagnostics, and safety guards.
   - Run the upstream compatibility scanner against a pinned Hermes revision,
     then against the current target revision before release. Require nonempty
     manifest and positive control; retain revision identifiers with results.
   - Test skill discovery/execution in an isolated HERMES_HOME and supported
     interpreter. Do not call this PluginManager coverage.
   - Optional bounded live read-only smoke: discover event/market and obtain a
     quote. Missing network/auth is a reported blocker, never a mock success.

3. Release gate
   - Synchronize pyproject.toml, package __version__, and skill version to 0.3.1
     only after tests pass and owner approves release.
   - Run lint, offline suite, build, twine check, install smoke, and compat check.
   - Existing 0.3.0 files on PyPI are immutable; skip-existing does not update them.
   - Publish through main-only trusted-publisher workflow; read back exact PyPI
     version and verify a fresh install outside checkout before claiming release.

## Optional 0.4.0: native plugin

Only if native tool discovery is desired:
- Add a pip entry point and a thin register(ctx) adapter using documented APIs,
  without importing host internal registries or monkeypatching host modules.
- Keep SDK independent and registration free of network calls/sidecar startup.
- Bundle the skill in the wheel and register it through the documented mechanism.
- Start with read-only tools. Trading exposure requires explicit safety review;
  a model-supplied confirmed=True boolean alone is not host-level user approval.
- Test actual PluginManager discovery, registration, tool invocation, and disabled
  states in isolation; run plugins doctor and compat. Verify pip and directory
  paths without duplicate registration before release.

## Non-goals

No Hermes self-update, global plugin migration, compatibility bypass, real order,
commit, push, or PyPI upload is authorized by this research plan.
