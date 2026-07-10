from __future__ import annotations

from unittest.mock import Mock, patch

from hermes_memory_metronix.client import MetronixClient


def test_search_memory_uses_rest_bearer_auth() -> None:
    client = MetronixClient(base_url="http://localhost:8000", auth_token="token")
    with patch("hermes_memory_metronix.client.requests.request") as req:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"records": []}
        req.return_value = response
        client.search_memory(workspace_id="MTRNIX", agent_id="agent-1", query="hello")
    assert req.call_args.kwargs["headers"]["Authorization"] == "Bearer token"


def test_search_memory_rejects_missing_auth() -> None:
    client = MetronixClient(base_url="http://localhost:8000")
    try:
        client.search_memory(workspace_id="MTRNIX", agent_id="agent-1", query="hello")
    except ValueError as exc:
        assert "auth" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


def test_store_memory_uses_rest_bearer_auth() -> None:
    client = MetronixClient(base_url="http://localhost:8000", auth_token="token")
    with patch("hermes_memory_metronix.client.requests.request") as req:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"memory": {"content": "stored"}}
        req.return_value = response
        result = client.store_memory(
            workspace_id="MTRNIX",
            agent_id="agent-1",
            content="stored",
            memory_type="fact",
        )
    assert result["memory"]["content"] == "stored"
    assert req.call_args.kwargs["headers"]["Authorization"] == "Bearer token"
    assert req.call_args.kwargs["json"]["content"] == "stored"
    assert req.call_args.args[1] == "http://localhost:8000/api/v1/memory/records?workspace_id=MTRNIX"


def test_delete_memory_uses_rest_bearer_auth() -> None:
    client = MetronixClient(base_url="http://localhost:8000", auth_token="token")
    with patch("hermes_memory_metronix.client.requests.request") as req:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}
        req.return_value = response
        result = client.delete_memory(
            workspace_id="MTRNIX",
            memory_id="memory-1",
        )
    assert result["ok"] is True
    assert req.call_args.kwargs["headers"]["Authorization"] == "Bearer token"
    assert req.call_args.args[1] == "http://localhost:8000/api/v1/memory/records/memory-1?workspace_id=MTRNIX"
