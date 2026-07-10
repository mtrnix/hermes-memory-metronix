from __future__ import annotations

import sys
import types


def pytest_sessionstart(session) -> None:
    if "agent.memory_provider" in sys.modules:
        return

    agent_module = types.ModuleType("agent")
    memory_provider_module = types.ModuleType("agent.memory_provider")

    class MemoryProvider:
        """Minimal Hermes MemoryProvider stub for local unit tests."""

    memory_provider_module.MemoryProvider = MemoryProvider
    agent_module.memory_provider = memory_provider_module
    sys.modules["agent"] = agent_module
    sys.modules["agent.memory_provider"] = memory_provider_module
