# Hermes Memory Metronix Repo Split Design

Date: 2026-07-08
Repository: `metronix-memory`
Related PR: `mtrnix/metronix-memory#331`
Related issue: `NousResearch/hermes-agent#57100`

## Goal

Extract the Hermes-native Metronix memory provider into a standalone repository
owned as a Hermes plugin project, while keeping `metronix-memory` as the
backend contract and documentation source of truth.

## Why split

The native Hermes integration has a different lifecycle from core Metronix:

- it depends on Hermes plugin and `MemoryProvider` interfaces,
- it needs Hermes-specific smoke testing and packaging,
- it should version independently from the Metronix backend,
- and it should be installable by Hermes users without carrying the full
  Metronix repository.

Keeping that code in `metronix-memory` makes the ownership boundary muddy and
encourages in-tree coupling. The better model is:

- `metronix-memory`: durable memory backend, REST/API semantics, auth model,
  data model, compatibility docs.
- `hermes-memory-metronix`: Hermes-native adapter that implements Hermes's
  `MemoryProvider` contract on top of Metronix APIs.

## Current state

This checkout contains a recovery target at
`standalone/hermes-memory-metronix/`, but the tree is not clean source today.
It mostly contains cache artifacts and compiled Python files, not a ready
standalone package. That means we should treat it as a recovery aid, not as the
final repository structure.

An earlier design spec,
`docs/superpowers/specs/2026-07-03-hermes-native-memory-and-wiki-design.md`,
already defined the intended plugin behavior:

- Hermes-native prefetch injection,
- write-through into Metronix,
- Hermes wiki migration support,
- runtime agent identity handling,
- and fail-open behavior.

This design does not replace that behavior. It defines where that behavior
should live and how to extract it safely.

## Recommended target boundary

### `metronix-memory` keeps

- REST and SDK-level memory contract used by the plugin.
- Auth semantics for plugin calls.
- Knowledge and agent-memory storage semantics.
- Compatibility documentation for Hermes integrations.
- Contract-level verification that published backend endpoints still match what
  the standalone plugin expects.

### `hermes-memory-metronix` owns

- Hermes `MemoryProvider` implementation.
- Hermes plugin packaging and installation instructions.
- Local config resolution for base URL, workspace, auth, and agent identity.
- Prefetch caching and formatting logic.
- Write-through mapping from Hermes turns into Metronix memory operations.
- Hermes-facing unit, integration, and smoke tests.
- Hermes wiki migration tooling if that remains part of the native plugin story.

## Extraction principles

### 1. Recover source intent, not generated artifacts

Do not ship `.pyc` files, `__pycache__`, or other generated remnants. They may
help recover code intent, but the standalone repo must be rebuilt as normal
source files with a clean package layout.

### 2. Keep the plugin thin

The plugin should adapt Hermes to Metronix, not reimplement Metronix behavior.
It should stay focused on:

- config and auth resolution,
- prefetch request and cache flow,
- write-through payload mapping,
- graceful degradation when Metronix is unavailable.

### 3. Prefer runtime Hermes identity

The plugin must use Hermes's active runtime agent identity by default. A fixed
`METRONIX_AGENT_ID` may be supported as an explicit override, but must not be
the accidental default because it risks cross-agent memory pollution.

### 4. Use REST auth for plugin data paths

The standalone plugin should use Metronix REST auth for store/search/delete
flows. MCP auth and REST auth must be documented and tested as separate
surfaces so the plugin does not send the wrong token shape to REST endpoints.

### 5. Fail open

Memory enrichment is valuable but should not make Hermes unusable. If Metronix
is unreachable or returns errors, the plugin should degrade cleanly rather than
crashing the chat flow.

## Rollout plan

### Phase 1: Recover and stabilize standalone source

Recover the plugin into a clean standalone source tree with normal repository
basics:

- `pyproject.toml`
- package layout under `src/` or an equivalent explicit module root
- `README.md`
- `LICENSE`
- `.gitignore`
- typed source files
- explicit tests

The recovered tree should preserve the intended behavior from the earlier
Hermes-native design, but it should no longer depend on source living inside
`metronix-memory`.

### Phase 2: Prove standalone verification

Before removing anything from `metronix-memory`, prove the standalone repo in
three layers:

- unit tests for config/auth/identity/prefetch/write-through/fail-open logic,
- integration tests against a local Metronix instance using REST auth,
- Hermes smoke verification using `hermes chat --memory-provider metronix`.

The smoke run should confirm both:

- prefetch material appears for the correct active agent and workspace,
- and new memories are written back under the correct active agent identity.

### Phase 3: Update `metronix-memory`

After the standalone repo is green:

- update Hermes docs in `metronix-memory` to point to the new repo,
- document version compatibility and verification steps,
- make the repo boundary explicit,
- and keep only backend contract guidance here.

### Phase 4: Remove or archive the in-repo scaffold

Only after the standalone repo has proven source, tests, and smoke coverage:

- remove or archive `standalone/hermes-memory-metronix/` from this repo,
- remove stale in-repo references that imply native Hermes support is maintained
  here,
- keep only documentation links and backend compatibility notes.

## Testing ownership

### Standalone repo test responsibilities

The standalone repo should own:

- config precedence tests,
- REST token vs email/password auth selection tests,
- runtime-vs-fixed agent identity tests,
- prefetch assembly and cache tests,
- write-through mapping tests,
- fail-open behavior tests,
- local Metronix integration tests,
- Hermes plugin discovery/load tests,
- and end-to-end Hermes smoke verification instructions.

### `metronix-memory` test responsibilities

This repo should not own Hermes plugin behavior tests after extraction. It
should keep only:

- API contract tests relevant to plugin calls,
- auth behavior tests for the backend endpoints the plugin uses,
- and docs/tests ensuring the published integration guidance remains accurate.

## Risks

### Recovery ambiguity

The current scaffold is incomplete and source recovery may be imperfect. We
should expect some reconstruction rather than a literal file move.

### Identity drift

If the plugin defaults to a static agent id, memory records may be stored under
the wrong Hermes identity.

### Auth-surface confusion

If MCP credentials are reused against REST endpoints, live smoke will fail with
401s or misleading backend errors.

### Premature deletion

If we remove the in-repo scaffold before the standalone repo is proven, we risk
losing the best available recovery hints.

## Non-goals

- Keeping native Hermes plugin code as a permanent in-tree feature of
  `metronix-memory`.
- Coupling plugin releases to Metronix backend releases.
- Rewriting Metronix backend behavior just to mirror Hermes plugin concerns.
- Treating the compiled recovery artifacts as shippable outputs.

## Recommendation

Proceed with a clean standalone split now.

The concrete strategy is:

1. Recover the plugin source from the existing scaffold and prior design intent.
2. Create and validate a standalone `hermes-memory-metronix` repository.
3. Move all Hermes-native testing and demo ownership there.
4. Reduce `metronix-memory` to backend contracts plus integration
   documentation.

This gives the cleanest long-term architecture with the lowest operational
confusion.
