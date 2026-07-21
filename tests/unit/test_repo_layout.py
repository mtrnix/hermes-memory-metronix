from __future__ import annotations

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
