# Hermes Agent Metronix Memory Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `hermes-memory-metronix` as a standalone Hermes memory-provider plugin and close the core acceptance criteria from `NousResearch/hermes-agent#57100`: prefetch injection, write-through, cross-profile sharing, config-gated behavior, and a credible upstream PR/demo package.

**Architecture:** Keep the implementation thin. The standalone repo owns Hermes-facing provider code, packaging, tests, and smoke instructions; `metronix-memory` remains the backend contract. Hermes upstream changes should be minimal and limited to the integration seam already present in Hermes, plus docs or tiny host changes only if the standalone plugin exposes a real gap.

**Tech Stack:** Python 3.11+, setuptools, pytest, requests, Hermes plugin/memory-provider interfaces, Metronix REST API.

## Global Constraints

- Do not add new runtime dependencies unless Hermes integration proves one is unavoidable.
- Prefer runtime Hermes agent identity over a static default; allow explicit override only via config.
- Use Metronix REST auth for plugin data paths; do not send MCP credentials to REST endpoints.
- Fail open: Metronix outages must not break Hermes chat.
- Keep plugin logic in `hermes-memory-metronix`; do not re-embed it into `metronix-memory`.
- Treat this checkout as a source workspace, not a complete git checkout of `hermes-agent`.

---

## Current Gap Summary

The current `hermes-memory-metronix` workspace already contains:

- `src/hermes_memory_metronix/config.py`
- `src/hermes_memory_metronix/client.py`
- `src/hermes_memory_metronix/provider.py`
- unit and integration tests

But it is still short of the issue acceptance criteria:

- no write-through implementation yet,
- no client store/delete flow,
- no cross-profile or write-scope behavior,
- no Hermes plugin metadata or load verification in this repo,
- no upstream `hermes-agent` checkout here to validate exact host touchpoints,
- no screencast/demo packaging yet.

### Task 1: Baseline the standalone plugin and remove recovery noise

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `tests/unit/test_repo_layout.py`
- Delete during execution: generated `__pycache__` content under `src/` and `tests/`
- Create if missing: `.gitignore`

**Interfaces:**
- Consumes: current package layout in `src/hermes_memory_metronix/`
- Produces: a clean standalone repo shape that can be cloned, tested, and installed without recovery artifacts

- [ ] **Step 1: Write the failing repository-shape test**

```python
from __future__ import annotations

from pathlib import Path


def test_repo_excludes_generated_python_cache() -> None:
    root = Path(__file__).resolve().parents[2]
    assert not any(root.rglob("__pycache__"))
    assert not any(root.rglob("*.pyc"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_repo_layout.py -v`
Expected: FAIL because `__pycache__` and `.pyc` files are present in the tree.

- [ ] **Step 3: Add ignore rules and remove generated artifacts**

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
dist/
build/
*.egg-info/
```

```markdown
## Development

python -m pytest tests/unit -v
RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_live_metronix.py -v
```

- [ ] **Step 4: Run tests to verify the tree is clean**

Run: `python -m pytest tests/unit/test_repo_layout.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .gitignore README.md pyproject.toml tests/unit/test_repo_layout.py
git commit -m "chore: clean standalone plugin repository layout"
```

### Task 2: Finish config and auth resolution for the standalone provider

**Files:**
- Modify: `src/hermes_memory_metronix/config.py`
- Modify: `src/hermes_memory_metronix/client.py`
- Modify: `tests/unit/test_config.py`
- Modify: `tests/unit/test_client.py`

**Interfaces:**
- Consumes: `ProviderConfig.from_env()`, `ProviderConfig.resolve_agent_id()`, `MetronixClient.search_memory()`
- Produces:
  - `ProviderConfig.prefetch_enabled: bool`
  - `ProviderConfig.prefetch_top_k: int`
  - `ProviderConfig.write_through: bool`
  - `ProviderConfig.write_scope: str`
  - `MetronixClient.store_memory(...) -> dict[str, Any]`
  - `MetronixClient.delete_memory(...) -> dict[str, Any]`

- [ ] **Step 1: Write failing config/auth tests**

```python
def test_runtime_agent_id_wins_when_no_override(monkeypatch) -> None:
    monkeypatch.setenv("METRONIX_BASE_URL", "http://localhost:8080")
    monkeypatch.setenv("METRONIX_WORKSPACE_ID", "team-brain")
    config = ProviderConfig.from_env()
    assert config.resolve_agent_id("runtime-agent") == "runtime-agent"


def test_explicit_agent_override_wins(monkeypatch) -> None:
    monkeypatch.setenv("METRONIX_BASE_URL", "http://localhost:8080")
    monkeypatch.setenv("METRONIX_WORKSPACE_ID", "team-brain")
    monkeypatch.setenv("METRONIX_AGENT_ID", "forced-agent")
    config = ProviderConfig.from_env()
    assert config.resolve_agent_id("runtime-agent") == "forced-agent"


def test_store_memory_uses_rest_bearer_auth() -> None:
    client = MetronixClient(base_url="http://localhost:8080", auth_token="token")
    with patch("hermes_memory_metronix.client.requests.request") as req:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"memory": {"content": "stored"}}
        req.return_value = response
        result = client.store_memory(
            workspace_id="team-brain",
            agent_id="runtime-agent",
            content="stored",
            memory_type="fact",
        )
    assert result["memory"]["content"] == "stored"
    assert req.call_args.kwargs["headers"]["Authorization"] == "Bearer token"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_config.py tests/unit/test_client.py -v`
Expected: FAIL because the new config fields and store/delete client methods do not exist yet.

- [ ] **Step 3: Implement minimal config and REST client expansion**

```python
@dataclass(slots=True)
class ProviderConfig:
    base_url: str
    workspace_id: str
    auth_token: str | None = None
    email: str | None = None
    password: str | None = None
    agent_id_override: str | None = None
    prefetch_enabled: bool = True
    prefetch_top_k: int = 8
    write_through: bool = True
    write_scope: str = "workspace"
```

```python
def store_memory(self, *, workspace_id: str, agent_id: str, content: str, memory_type: str) -> dict[str, Any]:
    response = requests.request(
        "POST",
        f"{self.base_url}/api/v1/memory",
        headers=self._headers(),
        json={
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "content": content,
            "memory_type": memory_type,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
```

- [ ] **Step 4: Run tests to verify config/auth behavior passes**

Run: `python -m pytest tests/unit/test_config.py tests/unit/test_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/hermes_memory_metronix/config.py src/hermes_memory_metronix/client.py tests/unit/test_config.py tests/unit/test_client.py
git commit -m "feat: add metronix provider config and rest write client"
```

### Task 3: Implement provider write-through and fail-open behavior

**Files:**
- Modify: `src/hermes_memory_metronix/provider.py`
- Modify: `tests/unit/test_provider.py`
- Modify: `tests/unit/test_fail_open.py`

**Interfaces:**
- Consumes:
  - `MetronixClient.search_memory(workspace_id: str, agent_id: str, query: str) -> dict[str, Any]`
  - `MetronixClient.store_memory(workspace_id: str, agent_id: str, content: str, memory_type: str) -> dict[str, Any]`
- Produces:
  - `MetronixMemoryProvider.queue_prefetch(query: str, *, session_id: str = "") -> None`
  - `MetronixMemoryProvider.on_memory_add(content: str, *, memory_type: str = "fact") -> None`
  - fail-open semantics for both read and write paths

- [ ] **Step 1: Write the failing provider tests for write-through**

```python
def test_on_memory_add_writes_to_metronix() -> None:
    client = FakeClient()
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8080", workspace_id="team-brain"),
        client=client,
        runtime_agent_id="agent-1",
    )
    provider.on_memory_add("Paris is my home base", memory_type="fact")
    assert client.store_calls == [
        {
            "workspace_id": "team-brain",
            "agent_id": "agent-1",
            "content": "Paris is my home base",
            "memory_type": "fact",
        }
    ]
```

```python
def test_write_through_fails_open() -> None:
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8080", workspace_id="team-brain"),
        client=BrokenClient(),
        runtime_agent_id="agent-1",
    )
    provider.on_memory_add("new memory", memory_type="fact")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_provider.py tests/unit/test_fail_open.py -v`
Expected: FAIL because `on_memory_add()` does not exist yet.

- [ ] **Step 3: Implement the smallest write-through path**

```python
def on_memory_add(self, content: str, *, memory_type: str = "fact") -> None:
    if not self._config.write_through:
        return
    try:
        self._client.store_memory(
            workspace_id=self._config.workspace_id,
            agent_id=self._agent_id(),
            content=content,
            memory_type=memory_type,
        )
    except Exception:
        return
```

- [ ] **Step 4: Run the provider tests**

Run: `python -m pytest tests/unit/test_provider.py tests/unit/test_fail_open.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/hermes_memory_metronix/provider.py tests/unit/test_provider.py tests/unit/test_fail_open.py
git commit -m "feat: add metronix memory write-through"
```

### Task 4: Prove cross-profile semantics and live backend compatibility

**Files:**
- Modify: `tests/integration/test_live_metronix.py`
- Modify: `docs/smoke.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: live Metronix REST auth and workspace configuration
- Produces:
  - a live integration test that verifies search plus write-through behavior
  - smoke instructions that validate multiple Hermes profiles bound to one Metronix workspace

- [ ] **Step 1: Write the failing integration assertions**

```python
@pytest.mark.integration
def test_live_store_search_delete_smoke() -> None:
    ...
    created = client.store_memory(
        workspace_id=workspace_id,
        agent_id=agent_id,
        content=smoke_content,
        memory_type="fact",
    )
    assert created["memory"]["content"] == smoke_content
```

- [ ] **Step 2: Run the integration test to verify the current gap**

Run: `RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_live_metronix.py -v`
Expected: FAIL until the client write path and cleanup flow are complete and valid credentials are supplied.

- [ ] **Step 3: Expand the live test and smoke guide**

```markdown
1. Start Hermes profile A with `hermes chat --memory-provider metronix`.
2. Add a memory through the native memory action.
3. Start Hermes profile B bound to the same Metronix workspace.
4. Ask a query that should recall the shared fact.
5. Verify the fact appears with the active runtime Hermes identity and not a hard-coded fallback id.
```

- [ ] **Step 4: Rerun integration verification**

Run: `RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_live_metronix.py -v`
Expected: PASS with valid REST auth and a live backend.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_live_metronix.py docs/smoke.md README.md
git commit -m "test: verify live metronix integration and cross-profile smoke flow"
```

### Task 5: Validate Hermes host integration in a real `hermes-agent` checkout

**Files:**
- Inspect in Hermes checkout: `agent/agent_init.py`
- Inspect in Hermes checkout: `hermes_cli/_parser.py`
- Inspect in Hermes checkout: `hermes_cli/main.py`
- Inspect in Hermes checkout: `hermes_cli/memory_setup.py`
- Inspect in Hermes checkout: `hermes_cli/subcommands/memory.py`
- Create or modify only if needed after inspection: provider discovery/docs/example config files in Hermes

**Interfaces:**
- Consumes: standalone plugin installed into `~/.hermes/plugins/metronix`
- Produces:
  - proof that Hermes can discover and use `metronix` without core changes, or
  - a minimal upstream patch if a real discovery/config seam is missing

- [ ] **Step 1: Clone or open a fresh Hermes checkout and write a compatibility checklist**

```text
Check 1: Hermes can list installed memory providers.
Check 2: `hermes chat --memory-provider metronix` selects the provider.
Check 3: runtime agent identity is passed into the provider.
Check 4: native memory add path calls provider write-through.
```

- [ ] **Step 2: Run the host smoke before touching Hermes core**

Run: `hermes chat --memory-provider metronix`
Expected: Either PASS with the standalone plugin, or a concrete failure pointing to one missing Hermes seam.

- [ ] **Step 3: If Hermes needs a patch, keep it tiny and issue-shaped**

```python
# Example target shape only if inspection proves a missing seam.
provider = load_memory_provider(name=args.memory_provider)
agent = build_agent(..., memory_provider=provider)
```

- [ ] **Step 4: Verify the Hermes-side acceptance criteria**

Run:

```bash
hermes memory providers
hermes chat --memory-provider metronix
```

Expected:

- provider is discoverable,
- prefetch occurs before a turn,
- `memory(action="add")` writes through,
- shared workspace recall works across profiles.

- [ ] **Step 5: Commit the minimal upstream patch**

```bash
git add agent/agent_init.py hermes_cli/_parser.py hermes_cli/main.py hermes_cli/memory_setup.py hermes_cli/subcommands/memory.py
git commit -m "feat: wire metronix memory provider into hermes host flow"
```

### Task 6: Prepare the PR, screencast, and social proof package

**Files:**
- Modify: `README.md`
- Modify: `docs/smoke.md`
- Create: `docs/demo-script.md`
- Create in Hermes checkout if needed: PR body draft under `docs/` or local notes

**Interfaces:**
- Consumes: passing plugin tests, Hermes smoke evidence, issue acceptance criteria
- Produces:
  - a mergeable plugin repo state
  - a tight upstream PR narrative
  - a 60-90 second screencast script and artifact checklist

- [ ] **Step 1: Write the demo script before recording**

```markdown
1. Show `hermes memory providers` with `metronix` available.
2. Start `hermes chat --memory-provider metronix`.
3. Ask a question that recalls an existing Metronix fact.
4. Add a new memory via Hermes native memory.
5. Query from a second profile bound to the same workspace.
6. Show the new fact being recalled.
```

- [ ] **Step 2: Draft the upstream PR message**

```markdown
Closes #57100.

This PR wires the standalone `hermes-memory-metronix` provider into the documented Hermes memory-provider flow and validates:
- prefetch injection,
- write-through from native memory add,
- runtime agent identity,
- cross-profile shared workspace recall.
```

- [ ] **Step 3: Record the screencast**

Run:

```bash
# use your normal screen recorder; keep the run under 90 seconds
```

Expected: one clean take showing recall, write-through, and cross-profile proof.

- [ ] **Step 4: Publish the share package**

```markdown
Built a standalone `hermes-memory-metronix` provider for @NousResearch Hermes:
- native prefetch injection
- write-through from memory add
- shared recall across profiles via Metronix

Issue: https://github.com/NousResearch/hermes-agent/issues/57100
Demo below. Happy to upstream and maintain it.
```

- [ ] **Step 5: Commit the docs/demo artifacts**

```bash
git add README.md docs/smoke.md docs/demo-script.md
git commit -m "docs: add metronix provider demo and upstream handoff notes"
```

## Recommended Execution Order

1. Finish Tasks 1-4 in `hermes-memory-metronix`.
2. Run unit tests locally until green.
3. Run the live Metronix integration test with REST auth.
4. Install the plugin into `~/.hermes/plugins/metronix`.
5. Execute Task 5 in a fresh `hermes-agent` checkout.
6. Only then open the upstream PR and record the screencast.

## Self-Review

- Spec coverage:
  - repo split boundary: covered by Tasks 1 and 6
  - prefetch injection: existing path validated in Tasks 3-5
  - write-through: implemented in Task 3
  - cross-profile sharing: validated in Tasks 4-5
  - fail-open behavior: Task 3
  - upstream Hermes alignment: Task 5
  - screencast and sharing: Task 6
- Placeholder scan:
  - the only intentionally variable line is the exact Hermes file list to change, because the host repo is not present in this workspace; Task 5 forces inspection before editing.
- Type consistency:
  - provider and client method names are consistent across Tasks 2-4.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-09-hermes-agent-metronix-memory-provider.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
