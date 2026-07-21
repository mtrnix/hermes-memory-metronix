from __future__ import annotations

from pathlib import Path


def test_plugin_package_is_the_only_provider_implementation() -> None:
    root = Path(__file__).resolve().parents[2]

    assert (root / "plugin" / "metronix" / "__init__.py").is_file()
    assert not (root / "src" / "hermes_memory_metronix").exists()


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
