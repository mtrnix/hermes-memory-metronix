from __future__ import annotations

import json
from pathlib import Path

from hermes_memory_metronix.config import ProviderConfig
from hermes_memory_metronix.provider import MetronixMemoryProvider


class FakeClient:
    def __init__(self) -> None:
        self.search_calls = []
        self.store_calls = []

    def search_memory(self, **kwargs):
        self.search_calls.append(kwargs)
        return {"records": [{"content": "remembered fact"}]}

    def store_memory(self, **kwargs):
        self.store_calls.append(kwargs)
        return {"ok": True}


def test_prefetch_reads_cached_value() -> None:
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX"),
        client=FakeClient(),
        runtime_agent_id="agent-1",
    )
    provider.queue_prefetch("hello", session_id="s1")
    assert "remembered fact" in provider.prefetch("hello", session_id="s1")


def test_on_session_switch_clears_old_cache() -> None:
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX"),
        client=FakeClient(),
        runtime_agent_id="agent-1",
    )
    provider.queue_prefetch("hello", session_id="s1")
    provider.on_session_switch("s2", parent_session_id="", reset=False, rewound=False)
    assert provider.prefetch("hello", session_id="s1") == ""


def test_on_memory_add_writes_to_metronix() -> None:
    client = FakeClient()
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX"),
        client=client,
        runtime_agent_id="agent-1",
    )

    provider.on_memory_add("Paris is my home base", memory_type="fact")

    assert client.store_calls == [
        {
            "workspace_id": "MTRNIX",
            "agent_id": "agent-1",
            "content": "Paris is my home base",
            "memory_type": "fact",
        }
    ]


def test_on_memory_add_respects_write_through_flag() -> None:
    client = FakeClient()
    provider = MetronixMemoryProvider(
        config=ProviderConfig(
            base_url="http://localhost:8000",
            workspace_id="MTRNIX",
            write_through=False,
        ),
        client=client,
        runtime_agent_id="agent-1",
    )

    provider.on_memory_add("do not store", memory_type="fact")

    assert client.store_calls == []


def test_initialize_sets_session_and_runtime_agent() -> None:
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX"),
        client=FakeClient(),
    )

    provider.initialize(
        "session-1",
        agent_identity="agent-1",
        hermes_home="/tmp/hermes-home",
    )

    assert provider.name == "metronix"
    assert provider._session_id == "session-1"
    assert provider._runtime_agent_id == "agent-1"


def test_on_memory_write_mirrors_add_action() -> None:
    client = FakeClient()
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX"),
        client=client,
        runtime_agent_id="agent-1",
    )

    provider.on_memory_write("add", "memory", "store this")

    assert client.store_calls == [
        {
            "workspace_id": "MTRNIX",
            "agent_id": "agent-1",
            "content": "store this",
            "memory_type": "memory",
        }
    ]


def test_get_config_schema_exposes_setup_fields() -> None:
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX"),
        client=FakeClient(),
    )

    schema = provider.get_config_schema()

    keys = {field["key"] for field in schema}
    assert "base_url" in keys
    assert "workspace_id" in keys
    assert "auth_token" in keys
    assert "prefetch_top_k" in keys
    assert "write_through" in keys


def test_save_config_writes_metronix_json(tmp_path: Path) -> None:
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="", workspace_id=""),
        client=FakeClient(),
    )

    provider.save_config(
        {
            "base_url": "http://localhost:8080",
            "workspace_id": "team-brain",
            "prefetch_top_k": "8",
            "write_through": "true",
            "write_scope": "workspace",
        },
        str(tmp_path),
    )

    payload = json.loads((tmp_path / "metronix.json").read_text())
    assert payload["base_url"] == "http://localhost:8080"
    assert payload["workspace_id"] == "team-brain"
    assert payload["prefetch_top_k"] == 8
    assert payload["write_through"] is True
