from __future__ import annotations

import importlib.util
from pathlib import Path


class _Collector:
    def __init__(self) -> None:
        self.provider = None

    def register_memory_provider(self, provider) -> None:
        self.provider = provider


def test_repo_root_registers_memory_provider() -> None:
    root = Path(__file__).resolve().parents[2]
    init_file = root / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "metronix_plugin",
        init_file,
        submodule_search_locations=[str(root)],
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    collector = _Collector()
    module.register(collector)

    assert collector.provider is not None
    assert collector.provider.name == "metronix"


def test_repo_root_includes_plugin_yaml() -> None:
    root = Path(__file__).resolve().parents[2]
    plugin_yaml = root / "plugin.yaml"
    assert plugin_yaml.exists()
    assert "name: metronix" in plugin_yaml.read_text()
