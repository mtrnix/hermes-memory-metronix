from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path
import tomllib


def test_plugin_package_is_the_only_provider_implementation() -> None:
    root = Path(__file__).resolve().parents[2]

    assert (root / "__init__.py").is_file()
    assert (root / "plugin.yaml").is_file()
    assert (root / "plugin" / "metronix" / "__init__.py").is_file()
    assert (root / "plugin" / "metronix" / "plugin.yaml").is_file()
    assert not (root / "src" / "hermes_memory_metronix").exists()


def test_plugin_metadata_is_declared_as_package_data() -> None:
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())

    assert project["tool"]["setuptools"]["package-data"]["metronix"] == ["plugin.yaml"]


def test_package_declares_memory_provider_entry_point() -> None:
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())

    assert project["project"]["entry-points"]["hermes_agent.memory_providers"] == {
        "metronix": "metronix:register"
    }


def test_installed_package_exposes_loadable_memory_provider_entry_point() -> None:
    matches = [
        entry_point
        for entry_point in entry_points(group="hermes_agent.memory_providers")
        if entry_point.name == "metronix"
    ]

    assert len(matches) == 1
    assert matches[0].value == "metronix:register"
    assert callable(matches[0].load())


def test_manifests_match_release_and_declared_hooks() -> None:
    root = Path(__file__).resolve().parents[2]

    root_manifest = (root / "plugin.yaml").read_text()
    package_manifest = (root / "plugin" / "metronix" / "plugin.yaml").read_text()

    assert "version: 2026.34.1" in root_manifest
    assert "version: 2026.34.1" in package_manifest
    assert "on_memory_write" in package_manifest
    assert "on_session_end" not in package_manifest


def test_repo_excludes_generated_python_cache() -> None:
    root = Path(__file__).resolve().parents[2]
    gitignore = (root / ".gitignore").read_text()
    assert "__pycache__/" in gitignore
    assert "*.py[cod]" in gitignore
    assert ".pytest_cache/" in gitignore
    assert ".DS_Store" in gitignore


def test_readme_documents_locked_local_checks() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text()
    assert "## Development" in readme
    assert "uv run --extra dev pytest tests/unit -v" in readme


def test_readme_documents_real_hermes_compatibility_check() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text()

    assert "HERMES_AGENT_SRC=/absolute/path/to/hermes-agent" in readme
    assert "tests/unit/test_real_abc_contract.py" in readme


def test_readme_discloses_turn_sync_privacy_boundary() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text()

    assert "`sync_turns` is enabled by default" in readme
    assert "user message and assistant response" in readme
    assert "complete `messages`" in readme
    assert "tool-call arguments, or tool results" in readme
