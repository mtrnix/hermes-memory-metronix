# hermes-memory-metronix

Standalone Hermes `MemoryProvider` backed by Metronix Memory.

This repository owns the Hermes-native adapter layer:

- Hermes plugin packaging
- config and auth resolution
- prefetch and write-through behavior
- Hermes-focused unit, integration, and smoke tests

Metronix backend contracts and MCP integration docs remain in the
`metronix-memory` repository.

## Status

This is a scaffold, not a finished public plugin release.

What it already does:

- Implements the Hermes `MemoryProvider` contract
- Prefetches relevant Metronix memory records before a turn
- Mirrors Hermes `memory(action="add")` writes into Metronix
- Optionally writes completed turns as session-scoped Metronix memory
- Supports bearer-token auth, with email/password login fallback

What is intentionally still conservative:

- No custom Hermes setup wizard yet
- No extra provider-specific model tools yet
- Prefetch currently targets `/api/v1/memory/search`
- Knowledge-document / page retrieval is left as a follow-up

## Layout

The installable Hermes plugin lives in:

- `plugin/metronix/`

Hermes discovers user-installed memory providers from:

- `~/.hermes/plugins/<name>/__init__.py`

## Local install for Hermes

Copy the plugin directory into your Hermes home:

```bash
mkdir -p ~/.hermes/plugins
cp -R plugin/metronix ~/.hermes/plugins/metronix
```

Then set Hermes to use it:

```yaml
memory:
  provider: metronix
```

Or per-session:

```bash
hermes chat --memory-provider metronix
```

## Plugin config

The plugin reads non-secret config from:

- `$HERMES_HOME/metronix.json`

And secrets from:

- `$HERMES_HOME/.env`
- process environment

Example `metronix.json`:

```json
{
  "base_url": "http://localhost:8000",
  "workspace_id": "MTRNIX",
  "agent_id": "hermes",
  "prefetch": true,
  "prefetch_top_k": 8,
  "prefetch_types": ["fact", "preference", "pinned"],
  "cite_sources": true,
  "write_through": true,
  "write_scope": "workspace",
  "sync_turns": true
}
```

Secrets:

```bash
METRONIX_AUTH_TOKEN=...
# or:
METRONIX_EMAIL=admin@metronix.local
METRONIX_PASSWORD=...
```

Important:

- `METRONIX_AUTH_TOKEN` must be a REST JWT or personal API key for `/api/v1/*`
- `METRONIX_MCP_API_KEY` is for `/mcp`, not `/api/v1/memory/*`
- if you provide both a bearer token and login credentials, the client will
  retry once with a fresh login JWT when the original bearer gets a `401`

## Mapping notes

Hermes write scopes map to Metronix scopes like this:

- `per_agent` -> `per_agent`
- `workspace` -> `global`
- `shared` -> `global`
- `session` -> `session`

The current prefetch path uses Metronix memory search, so `prefetch_types`
maps to Metronix memory kinds:

- `fact`
- `preference`
- `pinned`

`page` is not wired yet because the current scaffold does not call a unified
knowledge-search endpoint.

## Migrating an existing llm-wiki into Metronix

Hermes's bundled `llm-wiki` skill maintains a directory of markdown pages
(`entities/`, `concepts/`, `comparisons/`, `queries/`, `raw/`) at `$WIKI_PATH`
(default `~/wiki`). To bulk-ingest an existing wiki into Metronix's Knowledge
Base (chunked, embedded, searchable via `metronix_search_fast`/`metronix_get`):

```bash
python scripts/migrate_wiki.py \
  --wiki-path ~/wiki \
  --base-url http://localhost:8000 \
  --workspace-id MTRNIX \
  --auth-token "$METRONIX_AUTH_TOKEN"
```

Each page becomes a document with `source_type="hermes_llm_wiki"` and a
deterministic `doc_label` derived from its wiki-relative path, so re-running
the script updates existing documents instead of duplicating them. By
default, only `raw/`, `entities/`, `concepts/`, `comparisons/`, and
`queries/` are ingested; `SCHEMA.md`, `index.md`, `log*.md`, and
`_archive/**` are skipped (pass `--include-archive` to include archived
pages instead).

Requires `METRONIX_AUTH_TOKEN` to be a REST JWT or personal API key for
`/api/v1/*`, not `METRONIX_MCP_API_KEY`, which is for `/mcp` only.

## Development

Run the fast local checks:

```bash
uv run --extra dev pytest tests/unit -v
RUN_INTEGRATION_TESTS=1 uv run --extra dev pytest tests/integration/test_live_metronix.py -v
```

### Verify against Hermes

Clone a clean Hermes checkout separately, then verify both the current
`MemoryProvider` abstract base class and Hermes's real plugin loader:

```bash
HERMES_AGENT_SRC=/absolute/path/to/hermes-agent \
  uv run --extra dev pytest \
  tests/unit/test_real_abc_contract.py tests/unit/test_hermes_plugin.py -v
```

The compatibility tests skip with an explicit reason when `HERMES_AGENT_SRC`
does not point to a Hermes checkout. They should pass before publishing a
plugin release.
