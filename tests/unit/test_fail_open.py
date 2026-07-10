from __future__ import annotations

from hermes_memory_metronix.config import ProviderConfig
from hermes_memory_metronix.provider import MetronixMemoryProvider


class BrokenClient:
    def search_memory(self, **kwargs):
        raise RuntimeError("backend down")

    def store_memory(self, **kwargs):
        raise RuntimeError("backend down")


def test_prefetch_fails_open() -> None:
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX"),
        client=BrokenClient(),
        runtime_agent_id="agent-1",
    )
    provider.queue_prefetch("hello", session_id="s1")
    assert provider.prefetch("hello", session_id="s1") == ""


def test_write_through_fails_open() -> None:
    provider = MetronixMemoryProvider(
        config=ProviderConfig(base_url="http://localhost:8000", workspace_id="MTRNIX"),
        client=BrokenClient(),
        runtime_agent_id="agent-1",
    )

    provider.on_memory_add("new memory", memory_type="fact")
