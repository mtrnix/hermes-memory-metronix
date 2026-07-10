from __future__ import annotations

from pathlib import Path
import tomllib


def test_only_the_hermes_plugin_package_is_shipped() -> None:
    root = Path(__file__).resolve().parents[2]

    assert not (root / "src" / "hermes_memory_metronix").exists()
    assert (root / "plugin" / "metronix" / "plugin.yaml").is_file()


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


def test_readme_documents_local_checks() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text()
    assert "## Development" in readme
    assert "python3 -m pytest tests/unit -v" in readme
