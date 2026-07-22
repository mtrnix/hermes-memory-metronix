# Hermes Memory Provider Hardening Design

## Goal

Turn `hermes-memory-metronix` into a standalone, installable Hermes memory
provider that supplies native prefetch, write-through, optional turn sync, and
safe cross-profile sharing through the Metronix backend.

## Scope and placement

This is a standalone plugin project. It will not add a Metronix provider to
the Hermes core repository. The plugin is installed from a user plugin
directory (`~/.hermes/plugins/metronix`) or, later, a Python distribution.

`metronix-memory` remains responsible for persistence, retrieval, REST API
semantics, and credential issuance. This repository owns the Hermes adapter,
its packaging, configuration, tests, and operator documentation.

## Architecture

The installable plugin directory is the canonical Hermes-facing runtime:

```text
Hermes MemoryProvider lifecycle
  -> plugin/metronix/MetronixMemoryProvider
  -> plugin/metronix/MetronixClient
  -> Metronix REST API
```

The provider reads non-secret settings from `~/.hermes/metronix.json` and
secrets from the process environment. It derives the Metronix agent identity
from the active Hermes runtime unless an explicit override is configured.

`queue_prefetch()` fetches relevant records asynchronously and stores a
formatted result in a session-keyed cache. `prefetch()` only reads that cache.
`on_memory_write()` maps Hermes `add` operations to Metronix memory records.
`sync_turn()` optionally stores user and assistant turn content in session
scope. Network or backend failures warn when possible and otherwise fail open;
they never abort a Hermes chat.

## Configuration and security

- `METRONIX_BASE_URL` and `METRONIX_WORKSPACE_ID` identify the REST target.
- `METRONIX_AUTH_TOKEN`, or `METRONIX_EMAIL` plus `METRONIX_PASSWORD`,
  authenticate REST operations.
- MCP API keys are not accepted for `/api/v1/*` calls.
- `METRONIX_AGENT_ID` is an explicit override, not the default identity.
- `prefetch`, `write_through`, `write_scope`, and `sync_turns` remain opt-in
  operator controls with documented defaults.

## Acceptance criteria

1. A clean Hermes checkout loads the plugin through its real discovery loader
   and confirms the class satisfies the current `MemoryProvider` ABC.
2. Valid configuration makes the provider available; incomplete configuration
   leaves it unavailable without crashing Hermes.
3. Prefetch returns only configured record kinds, is scoped correctly, and
   does not issue a request from the synchronous `prefetch()` path.
4. `memory(action="add")` creates one correctly scoped Metronix record when
   write-through is enabled.
5. Turn sync creates session-scoped records only when enabled.
6. Client errors leave prefetch empty and write/sync operations non-fatal.
7. The README provides exact installation, configuration, verification, and
   removal instructions.

## Verification strategy

Fast unit tests cover configuration precedence, scope and kind mapping, cache
behavior, REST request formation, fail-open behavior, and plugin registration.
Compatibility tests use `HERMES_AGENT_SRC` pointing at a clean Hermes checkout
to exercise the real ABC and loader. Live Metronix tests are opt-in through
`RUN_INTEGRATION_TESTS=1`; they never run from the default test command.

Manual acceptance installs the canonical plugin directory into a disposable
Hermes home, verifies provider discovery, confirms prefetch and write-through,
then repeats a chat with the backend unreachable to prove fail-open behavior.
