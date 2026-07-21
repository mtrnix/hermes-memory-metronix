# Hermes Memory Provider Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `hermes-memory-metronix` as a standalone Hermes plugin with one canonical runtime implementation, current-Hermes compatibility checks, and operator-ready documentation.

**Architecture:** `plugin/metronix/` is the canonical runtime package copied to `~/.hermes/plugins/metronix`. It implements the Hermes `MemoryProvider` lifecycle and calls Metronix REST through its colocated client. Remove the legacy `src/hermes_memory_metronix/` package after moving any required contract behavior, preventing two provider implementations from drifting.

**Tech Stack:** Python 3.11+, setuptools, pytest, requests, Hermes `MemoryProvider`, Metronix REST API.

## Global Constraints

- Do not add runtime dependencies.
- Use REST credentials only for `/api/v1/*`; never send an MCP key to REST endpoints.
- Prefer runtime Hermes agent identity; accept `METRONIX_AGENT_ID` only as an explicit override.
- Network failures must fail open and never break Hermes chat.
- Live integration tests run only with `RUN_INTEGRATION_TESTS=1` and explicit credentials.
- Keep the provider standalone; do not modify Hermes core.

---

### Task 1: Establish a reproducible test baseline

**Files:**
- Modify: `README.md`
- Modify: `tests/unit/test_repo_layout.py`

**Interfaces:**
- Consumes: the locked `uv.lock` dependency graph.
- Produces: documented, reproducible `uv run --extra dev pytest` verification.

- [ ] **Step 1: Write the failing documentation test**

```python
def test_readme_uses_the_locked_uv_test_command() -> None:
    root = Path(__file__).resolve().parents[2]
    assert "uv run --extra dev pytest tests/unit -v" in (root / "README.md").read_text()
```

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev pytest tests/unit/test_repo_layout.py::test_readme_uses_the_locked_uv_test_command -v`

Expected: FAIL because README currently recommends `python3 -m pytest`.

- [ ] **Step 3: Implement the minimal documentation change**

```markdown
uv run --extra dev pytest tests/unit -v
RUN_INTEGRATION_TESTS=1 uv run --extra dev pytest tests/integration/test_live_metronix.py -v
```

- [ ] **Step 4: Verify GREEN and baseline**

Run: `uv run --extra dev pytest tests/unit -v`

Expected: PASS, or stop and resolve any pre-existing failure before provider changes.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/unit/test_repo_layout.py
git commit -m "docs: document locked plugin test command"
```

### Task 2: Make `plugin/metronix` the sole runtime provider

**Files:**
- Modify: `__init__.py`
- Modify: `pyproject.toml`
- Delete: `src/hermes_memory_metronix/__init__.py`
- Delete: `src/hermes_memory_metronix/client.py`
- Delete: `src/hermes_memory_metronix/config.py`
- Delete: `src/hermes_memory_metronix/provider.py`
- Modify: `tests/unit/test_repo_layout.py`
- Modify: `tests/unit/test_hermes_plugin.py`

**Interfaces:**
- Consumes: `metronix.MetronixMemoryProvider` and `metronix.register(ctx)`.
- Produces: one provider import path used by both direct installation and the repository registration adapter.

- [ ] **Step 1: Write failing layout tests**

```python
def test_repo_has_one_provider_implementation() -> None:
    root = Path(__file__).resolve().parents[2]
    assert not (root / "src" / "hermes_memory_metronix").exists()

def test_root_registers_the_installable_provider() -> None:
    module = _load_root_plugin_module()
    collector = _Collector()
    module.register(collector)
    assert collector.provider.__class__.__module__ == "metronix"
```

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev pytest tests/unit/test_repo_layout.py::test_repo_has_one_provider_implementation -v`

Expected: FAIL because `src/hermes_memory_metronix` exists.

- [ ] **Step 3: Implement the canonical import**

```python
_ROOT = Path(__file__).resolve().parent
_PLUGIN = _ROOT / "plugin"
if str(_PLUGIN) not in sys.path:
    sys.path.insert(0, str(_PLUGIN))

from metronix import MetronixMemoryProvider
```

Remove the legacy source package and make package discovery search only `plugin`.

- [ ] **Step 4: Verify GREEN**

Run: `uv run --extra dev pytest tests/unit/test_repo_layout.py tests/unit/test_hermes_plugin.py -v`

Expected: PASS; real loader remains skipped until `HERMES_AGENT_SRC` is supplied.

- [ ] **Step 5: Commit**

```bash
git add -A src __init__.py pyproject.toml tests/unit/test_repo_layout.py tests/unit/test_hermes_plugin.py
git commit -m "refactor: make Hermes plugin package canonical"
```

### Task 3: Lock the provider lifecycle to observable behavior

**Files:**
- Modify: `plugin/metronix/__init__.py`
- Modify: `plugin/metronix/client.py`
- Modify: `tests/unit/test_prefetch_and_write.py`
- Modify: `tests/unit/test_prefetch_cache.py`
- Modify: `tests/unit/test_config_resolution.py`
- Modify: `tests/unit/test_client.py`

**Interfaces:**
- Consumes: `MetronixClient.search_memory(query, top_k, agent_id)` and `create_memory(content, agent_id, scope, kind, source_type, ...)`.
- Produces: session-cached prefetch, configured-scope write-through, optional session turn sync, and fail-open hooks.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_prefetch_reads_only_the_session_cache(monkeypatch) -> None:
    provider = _provider_with_client(FakeClient())
    provider._prefetch_cache["session-a"] = "cached context"
    assert provider.prefetch("ignored", session_id="session-a") == "cached context"

def test_memory_add_maps_workspace_scope_to_global(monkeypatch) -> None:
    client = FakeClient()
    provider = _provider_with_client(client, write_scope="workspace")
    _run_inline_threads(monkeypatch)
    provider.on_memory_write("add", "user", "I prefer tea")
    assert client.creates[0]["scope"] == "global"
    assert client.creates[0]["kind"] == "preference"

def test_prefetch_failure_is_empty_and_warns(monkeypatch) -> None:
    warnings: list[str] = []
    provider = _provider_with_client(BrokenClient(), warning_callback=warnings.append)
    _run_inline_threads(monkeypatch)
    provider.queue_prefetch("query", session_id="session-a")
    assert provider.prefetch("query", session_id="session-a") == ""
    assert warnings == ["Metronix prefetch failed: unavailable"]
```

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev pytest tests/unit/test_prefetch_and_write.py tests/unit/test_config_resolution.py -v`

Expected: FAIL only for the added assertions until provider behavior and fake clients agree on the payload contract.

- [ ] **Step 3: Implement the smallest behavior**

Keep `prefetch()` cache-only. In the asynchronous write closure, call `create_memory()` with `_map_write_scope()`, `_infer_kind()`, `source_type="hermes_memory_write"`, tags `["hermes", target]`, and forwarded metadata. Catch every client exception in the background closure and call `_warn()`.

- [ ] **Step 4: Verify GREEN**

Run: `uv run --extra dev pytest tests/unit/test_prefetch_and_write.py tests/unit/test_prefetch_cache.py tests/unit/test_config_resolution.py tests/unit/test_client.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugin/metronix tests/unit/test_prefetch_and_write.py tests/unit/test_prefetch_cache.py tests/unit/test_config_resolution.py tests/unit/test_client.py
git commit -m "feat: harden Metronix memory lifecycle"
```

### Task 4: Prove current Hermes compatibility and document operation

**Files:**
- Modify: `README.md`
- Modify: `docs/smoke.md`
- Modify: `TEST_PLAN.md`
- Modify: `tests/unit/test_real_abc_contract.py`
- Modify: `tests/unit/test_hermes_plugin.py`
- Modify: `tests/unit/test_repo_layout.py`

**Interfaces:**
- Consumes: a clean Hermes checkout supplied through `HERMES_AGENT_SRC`.
- Produces: reproducible compatibility commands and an operator guide that separates REST and MCP authentication.

- [ ] **Step 1: Write the failing operator-documentation test**

```python
def test_readme_contains_real_hermes_compatibility_command() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text()
    assert "HERMES_AGENT_SRC=/absolute/path/to/hermes-agent" in readme
    assert "tests/unit/test_real_abc_contract.py" in readme
```

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev pytest tests/unit/test_repo_layout.py::test_readme_contains_real_hermes_compatibility_command -v`

Expected: FAIL because README does not include the command.

- [ ] **Step 3: Document exact installation and verification**

```bash
mkdir -p ~/.hermes/plugins
cp -R plugin/metronix ~/.hermes/plugins/metronix
HERMES_AGENT_SRC=/absolute/path/to/hermes-agent \
  uv run --extra dev pytest tests/unit/test_real_abc_contract.py tests/unit/test_hermes_plugin.py -v
hermes memory providers
hermes chat --memory-provider metronix
```

Document that `METRONIX_AUTH_TOKEN` is a REST JWT/personal key and that `METRONIX_MCP_API_KEY` cannot authenticate REST provider calls.

- [ ] **Step 4: Run offline and real-Hermes verification**

Run: `uv run --extra dev pytest tests/unit -v`

Run: `HERMES_AGENT_SRC=/absolute/path/to/hermes-agent uv run --extra dev pytest tests/unit/test_real_abc_contract.py tests/unit/test_hermes_plugin.py -v`

Expected: offline tests PASS; compatibility tests PASS with a clean checkout or SKIP with an explicit missing-checkout reason.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/smoke.md TEST_PLAN.md tests/unit/test_real_abc_contract.py tests/unit/test_hermes_plugin.py tests/unit/test_repo_layout.py
git commit -m "docs: add Hermes provider installation verification"
```

## Final verification

- [ ] Run `uv run --extra dev pytest tests/unit -v`.
- [ ] Run real-Hermes contract and loader tests with a clean `HERMES_AGENT_SRC` checkout.
- [ ] Run live tests only with explicit non-production credentials:

```bash
RUN_INTEGRATION_TESTS=1 uv run --extra dev pytest tests/integration/test_live_metronix.py -v
```

- [ ] Inspect `git status --short` and `git log --oneline main..HEAD` before publishing.
