from __future__ import annotations

import importlib
import os
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_METRONIX_DIR = PROJECT_ROOT / "plugin" / "metronix"
HERMES_AGENT_SRC = os.environ.get("HERMES_AGENT_SRC", "")

pytestmark = pytest.mark.skipif(
    not Path(HERMES_AGENT_SRC, "agent", "memory_provider.py").is_file(),
    reason=f"HERMES_AGENT_SRC checkout not found at {HERMES_AGENT_SRC!r}",
)


def test_provider_is_real_memory_provider_subclass():
    from agent.memory_provider import MemoryProvider
    from metronix import MetronixMemoryProvider

    assert issubclass(MetronixMemoryProvider, MemoryProvider)
    assert isinstance(MetronixMemoryProvider(), MemoryProvider)


def test_plugin_loads_via_real_hermes_loader():
    if HERMES_AGENT_SRC not in sys.path:
        sys.path.insert(0, HERMES_AGENT_SRC)
    plugins_memory = importlib.import_module("plugins.memory")

    provider = plugins_memory._load_provider_from_dir(PLUGIN_METRONIX_DIR)

    assert provider is not None
    assert provider.name == "metronix"


def test_installed_repository_root_loads_via_real_hermes_discovery(tmp_path, monkeypatch):
    if HERMES_AGENT_SRC not in sys.path:
        sys.path.insert(0, HERMES_AGENT_SRC)
    plugins_memory = importlib.import_module("plugins.memory")

    installed_plugin = tmp_path / "plugins" / "metronix"
    installed_plugin.mkdir(parents=True)
    shutil.copy2(PROJECT_ROOT / "__init__.py", installed_plugin / "__init__.py")
    shutil.copy2(PROJECT_ROOT / "plugin.yaml", installed_plugin / "plugin.yaml")
    shutil.copytree(PROJECT_ROOT / "plugin", installed_plugin / "plugin")
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    assert plugins_memory.find_provider_dir("metronix") == installed_plugin

    provider = plugins_memory.load_memory_provider("metronix")

    assert provider is not None
    assert provider.name == "metronix"
