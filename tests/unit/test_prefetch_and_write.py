from __future__ import annotations

import threading

from metronix import MetronixMemoryProvider


def test_queue_prefetch_populates_cache_and_prefetch_reads_it():
    provider = MetronixMemoryProvider()
    provider._config = {
        "prefetch": True,
        "prefetch_top_k": 8,
        "prefetch_types": ["preference", "pinned"],
        "cite_sources": True,
        "write_scope": "workspace",
    }
    provider._agent_id = "hermes"
    provider._session_id = "sess-1"

    class FakeClient:
        def search_memory(self, **kwargs):
            return [
                {"record": {"id": "a1", "kind": "fact", "content": "ignore me"}},
                {"record": {"id": "b2", "kind": "preference", "content": "User likes terse answers"}},
                {"record": {"id": "c3", "kind": "pinned", "content": "Project codename is Atlas"}},
            ]

    provider._client = FakeClient()
    assert provider.prefetch("what do you know?", session_id="sess-1") == ""

    provider.queue_prefetch("what do you know?", session_id="sess-1")
    provider.shutdown()
    result = provider.prefetch("what do you know?", session_id="sess-1")

    assert "<memory-context>" in result
    assert "[b2] User likes terse answers" in result
    assert "[c3] Project codename is Atlas" in result
    assert "ignore me" not in result


def test_queue_prefetch_skips_whitespace_only_query():
    provider = MetronixMemoryProvider()
    provider._config = {"prefetch": True}
    search_calls: list[dict] = []

    class FakeClient:
        def search_memory(self, **kwargs):
            search_calls.append(kwargs)
            return []

    provider._client = FakeClient()
    provider.queue_prefetch(" \t\n ")

    assert search_calls == []


def test_queue_prefetch_includes_agent_identity_for_workspace_reads():
    provider = MetronixMemoryProvider()
    provider._config = {"prefetch": True, "write_scope": "workspace"}
    provider._agent_id = "hermes"
    search_calls: list[dict] = []

    class FakeClient:
        def search_memory(self, **kwargs):
            search_calls.append(kwargs)
            return []

    provider._client = FakeClient()
    provider.queue_prefetch("terminal theme")
    provider.shutdown()

    assert search_calls == [
        {"query": "terminal theme", "top_k": 8, "agent_id": "hermes"}
    ]


def test_on_memory_write_posts_expected_payload():
    provider = MetronixMemoryProvider()
    provider._config = {"write_through": True, "write_scope": "workspace"}
    provider._agent_id = "hermes"
    calls: list[dict] = []

    class FakeClient:
        def create_memory(self, **kwargs):
            calls.append(kwargs)
            return {"id": "mem-1"}

    provider._client = FakeClient()
    provider.on_memory_write("add", "user", "Prefers black coffee", metadata={"source": "test"})
    provider.shutdown()

    assert len(calls) == 1
    assert calls[0]["scope"] == "global"
    assert calls[0]["kind"] == "preference"
    assert calls[0]["source_type"] == "hermes_memory_write"
    assert calls[0]["tags"] == ["hermes", "user"]
    assert calls[0]["metadata"]["target"] == "user"
    assert calls[0]["metadata"]["source"] == "test"


def test_sync_turn_writes_session_records():
    provider = MetronixMemoryProvider()
    provider._config = {"sync_turns": True}
    provider._agent_id = "hermes"
    provider._session_id = "sess-123"
    calls: list[dict] = []

    class FakeClient:
        def create_memory(self, **kwargs):
            calls.append(kwargs)
            return {"id": "mem"}

    provider._client = FakeClient()
    provider.sync_turn("hello", "world")
    provider.shutdown()

    assert len(calls) == 2
    assert calls[0]["scope"] == "session"
    assert calls[0]["session_id"] == "sess-123"
    assert calls[1]["scope"] == "session"
    assert calls[1]["metadata"]["role"] == "assistant"


def test_queue_prefetch_fail_open_invokes_warning_callback():
    provider = MetronixMemoryProvider()
    provider._config = {"prefetch": True, "prefetch_top_k": 8, "prefetch_types": ["fact"]}
    provider._session_id = "sess-1"
    warnings: list[str] = []
    provider._warning_callback = warnings.append

    class BrokenClient:
        def search_memory(self, **kwargs):
            raise RuntimeError("boom")

    provider._client = BrokenClient()
    provider.queue_prefetch("test", session_id="sess-1")
    provider.shutdown()

    assert provider.prefetch("test", session_id="sess-1") == ""
    assert warnings
    assert "Metronix prefetch failed" in warnings[0]


def test_background_writes_are_ordered_and_shutdown_flushes_them() -> None:
    provider = MetronixMemoryProvider()
    provider._config = {"write_through": True, "write_scope": "workspace"}
    provider._agent_id = "hermes"
    first_started = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()
    calls: list[str] = []

    class BlockingClient:
        def create_memory(self, **kwargs):
            content = kwargs["content"]
            if content == "first":
                first_started.set()
                assert release_first.wait(timeout=2)
            else:
                second_started.set()
            calls.append(content)
            return {"id": content}

    provider._client = BlockingClient()
    provider.on_memory_write("add", "memory", "first")
    assert first_started.wait(timeout=1)
    provider.on_memory_write("add", "memory", "second")

    assert not second_started.wait(timeout=0.1)

    shutdown_done = threading.Event()

    def shutdown_provider() -> None:
        provider.shutdown()
        shutdown_done.set()

    shutdown_thread = threading.Thread(target=shutdown_provider)
    shutdown_thread.start()
    assert not shutdown_done.wait(timeout=0.1)

    release_first.set()
    shutdown_thread.join(timeout=2)

    assert shutdown_done.is_set()
    assert calls == ["first", "second"]


def test_shutdown_is_idempotent_and_rejects_new_background_work() -> None:
    provider = MetronixMemoryProvider()
    provider._config = {"write_through": True, "write_scope": "workspace"}
    calls: list[str] = []

    class FakeClient:
        def create_memory(self, **kwargs):
            calls.append(kwargs["content"])
            return {"id": "mem"}

    provider._client = FakeClient()
    provider.shutdown()
    provider.shutdown()
    provider.on_memory_write("add", "memory", "after shutdown")

    assert calls == []
