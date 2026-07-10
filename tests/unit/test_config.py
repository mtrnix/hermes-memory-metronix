from __future__ import annotations

from hermes_memory_metronix.config import ProviderConfig


def test_from_env_reads_provider_settings(monkeypatch) -> None:
    monkeypatch.setenv("METRONIX_BASE_URL", "http://localhost:8080/")
    monkeypatch.setenv("METRONIX_WORKSPACE_ID", "team-brain")
    monkeypatch.setenv("METRONIX_AUTH_TOKEN", "rest-token")
    monkeypatch.setenv("METRONIX_PREFETCH_TOP_K", "8")
    monkeypatch.setenv("METRONIX_WRITE_THROUGH", "false")
    monkeypatch.setenv("METRONIX_WRITE_SCOPE", "workspace")

    cfg = ProviderConfig.from_env()

    assert cfg.base_url == "http://localhost:8080"
    assert cfg.workspace_id == "team-brain"
    assert cfg.auth_token == "rest-token"
    assert cfg.prefetch_top_k == 8
    assert cfg.write_through is False
    assert cfg.write_scope == "workspace"


def test_from_hermes_supports_metronix_mcp_style_names(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("METRONIX_URL", "http://localhost:8000/mcp")
    monkeypatch.delenv("METRONIX_BASE_URL", raising=False)
    monkeypatch.delenv("METRONIX_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("METRONIX_AGENT_ID", raising=False)
    monkeypatch.setenv("DEFAULT_WORKSPACE_ID", "MTRNIX")
    monkeypatch.setenv("AGENT_UUID", "agent-uuid-1")

    cfg = ProviderConfig.from_hermes(str(tmp_path))

    assert cfg.base_url == "http://localhost:8000"
    assert cfg.workspace_id == "MTRNIX"
    assert cfg.agent_id_override == "agent-uuid-1"


def test_runtime_agent_id_wins_when_no_override() -> None:
    cfg = ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX")
    assert cfg.resolve_agent_id("runtime-agent") == "runtime-agent"


def test_explicit_override_beats_runtime_agent() -> None:
    cfg = ProviderConfig(
        base_url="http://localhost:8000",
        workspace_id="MTRNIX",
        agent_id_override="fixed-agent",
    )
    assert cfg.resolve_agent_id("runtime-agent") == "fixed-agent"


def test_resolve_agent_id_rejects_missing_runtime_and_override() -> None:
    cfg = ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX")
    try:
        cfg.resolve_agent_id(None)
    except ValueError as exc:
        assert "agent identity" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


def test_config_is_available_when_rest_settings_present() -> None:
    cfg = ProviderConfig(
        base_url="http://localhost:8000",
        workspace_id="MTRNIX",
        auth_token="token",
    )
    assert cfg.base_url
    assert cfg.workspace_id
