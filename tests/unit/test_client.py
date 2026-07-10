from __future__ import annotations

from unittest.mock import Mock, patch

from hermes_memory_metronix.client import MetronixClient as SrcMetronixClient
from metronix.client import MetronixClient as PluginMetronixClient


class _Response:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.content = b"{}"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._payload


def test_search_memory_uses_rest_bearer_auth() -> None:
    client = SrcMetronixClient(base_url="http://localhost:8000", auth_token="token")
    with patch("hermes_memory_metronix.client.requests.request") as req:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"records": []}
        req.return_value = response
        client.search_memory(workspace_id="MTRNIX", agent_id="agent-1", query="hello")
    assert req.call_args.kwargs["headers"]["Authorization"] == "Bearer token"


def test_search_memory_rejects_missing_auth() -> None:
    client = SrcMetronixClient(base_url="http://localhost:8000")
    try:
        client.search_memory(workspace_id="MTRNIX", agent_id="agent-1", query="hello")
    except ValueError as exc:
        assert "auth" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


def test_store_memory_uses_rest_bearer_auth() -> None:
    client = SrcMetronixClient(base_url="http://localhost:8000", auth_token="token")
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
    client = SrcMetronixClient(base_url="http://localhost:8000", auth_token="token")
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


def test_plugin_request_appends_workspace_and_bearer_header(monkeypatch):
    seen: dict[str, object] = {}

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        del kwargs
        seen["method"] = method
        seen["url"] = url
        seen["headers"] = headers
        seen["timeout"] = timeout
        return _Response({"results": []})

    client = PluginMetronixClient(
        base_url="http://localhost:8000",
        workspace_id="MTRNIX",
        auth_token="token-123",
    )
    monkeypatch.setattr(client._session, "request", fake_request)

    client.search_memory(query="hello", top_k=3)

    assert seen["method"] == "POST"
    assert seen["url"] == "http://localhost:8000/api/v1/memory/search?workspace_id=MTRNIX"
    assert seen["headers"]["Authorization"] == "Bearer token-123"


def test_plugin_login_fallback_caches_token(monkeypatch):
    login_calls: list[object] = []
    request_calls: list[object] = []

    def fake_post(url, json=None, timeout=None):
        login_calls.append((url, json, timeout))
        return _Response({"token": "jwt-abc"})

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        del kwargs
        request_calls.append((method, url, headers, timeout))
        return _Response({"status": "ok"})

    client = PluginMetronixClient(
        base_url="http://localhost:8000",
        workspace_id="MTRNIX",
        email="admin@example.com",
        password="password",
    )
    monkeypatch.setattr(client._session, "post", fake_post)
    monkeypatch.setattr(client._session, "request", fake_request)

    client.ping()
    client.ping()

    assert len(login_calls) == 1
    assert len(request_calls) == 2
    assert request_calls[0][2]["Authorization"] == "Bearer jwt-abc"


def test_plugin_request_retries_with_login_on_401(monkeypatch):
    login_calls: list[object] = []
    request_calls: list[object] = []

    def fake_post(url, json=None, timeout=None):
        login_calls.append((url, json, timeout))
        return _Response({"token": "jwt-fresh"})

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        del kwargs
        request_calls.append((method, url, headers, timeout))
        if len(request_calls) == 1:
            return _Response({"detail": "unauthorized"}, status_code=401)
        return _Response({"status": "ok"})

    client = PluginMetronixClient(
        base_url="http://localhost:8000",
        workspace_id="MTRNIX",
        auth_token="mcp-token-not-rest-token",
        email="admin@example.com",
        password="password",
    )
    monkeypatch.setattr(client._session, "post", fake_post)
    monkeypatch.setattr(client._session, "request", fake_request)

    payload = client.ping()

    assert payload["status"] == "ok"
    assert len(request_calls) == 2
    assert len(login_calls) == 1
    assert request_calls[0][2]["Authorization"] == "Bearer mcp-token-not-rest-token"
    assert request_calls[1][2]["Authorization"] == "Bearer jwt-fresh"


def test_plugin_store_document_posts_expected_payload(monkeypatch):
    seen: dict[str, object] = {}

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        del headers, timeout
        seen["method"] = method
        seen["url"] = url
        seen["json"] = kwargs.get("json")
        return _Response({"success": True, "doc_label": "hermes-wiki-abc123", "chunks_stored": 2})

    client = PluginMetronixClient(
        base_url="http://localhost:8000",
        workspace_id="MTRNIX",
        auth_token="token-123",
    )
    monkeypatch.setattr(client._session, "request", fake_request)

    result = client.store_document(
        content="page body",
        title="Page",
        doc_label="hermes-wiki-abc123",
        source_type="hermes_llm_wiki",
        metadata={"page_type": "entities"},
    )

    assert seen["method"] == "POST"
    assert seen["url"] == "http://localhost:8000/api/v1/knowledge/store?workspace_id=MTRNIX"
    assert seen["json"] == {
        "content": "page body",
        "source_type": "hermes_llm_wiki",
        "title": "Page",
        "doc_label": "hermes-wiki-abc123",
        "metadata": {"page_type": "entities"},
    }
    assert result["doc_label"] == "hermes-wiki-abc123"
