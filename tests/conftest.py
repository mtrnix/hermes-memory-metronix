from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_root in (PROJECT_ROOT / "plugin",):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


HERMES_AGENT_SRC = os.environ.get("HERMES_AGENT_SRC", "")
_hermes_agent_path = Path(HERMES_AGENT_SRC) if HERMES_AGENT_SRC else None
_real_memory_provider_file = (
    _hermes_agent_path / "agent" / "memory_provider.py" if _hermes_agent_path else None
)
HAS_REAL_HERMES_AGENT = bool(_real_memory_provider_file and _real_memory_provider_file.is_file())


def _load_real_memory_provider_abc(hermes_agent_src: Path) -> None:
    """Register agent.memory_provider without importing agent/__init__.py."""
    if "agent" not in sys.modules:
        agent_pkg = types.ModuleType("agent")
        agent_pkg.__path__ = [str(hermes_agent_src / "agent")]
        sys.modules["agent"] = agent_pkg

    spec = importlib.util.spec_from_file_location(
        "agent.memory_provider",
        str(hermes_agent_src / "agent" / "memory_provider.py"),
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Hermes MemoryProvider ABC")
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent.memory_provider"] = module
    spec.loader.exec_module(module)
    setattr(sys.modules["agent"], "memory_provider", module)


def pytest_sessionstart(session) -> None:
    del session

    if HAS_REAL_HERMES_AGENT:
        if str(_hermes_agent_path) not in sys.path:
            sys.path.insert(0, str(_hermes_agent_path))
        if "agent.memory_provider" not in sys.modules:
            _load_real_memory_provider_abc(_hermes_agent_path)
        return

    agent_module = types.ModuleType("agent")
    memory_provider_module = types.ModuleType("agent.memory_provider")

    class MemoryProvider:
        """Minimal Hermes MemoryProvider stub for local unit tests."""

    memory_provider_module.MemoryProvider = MemoryProvider
    agent_module.memory_provider = memory_provider_module
    sys.modules["agent"] = agent_module
    sys.modules["agent.memory_provider"] = memory_provider_module
