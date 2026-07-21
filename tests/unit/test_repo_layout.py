from __future__ import annotations

from pathlib import Path


def test_provider_exports_exist() -> None:
    from hermes_memory_metronix.client import MetronixClient
    from hermes_memory_metronix.config import ProviderConfig
    from hermes_memory_metronix.provider import MetronixMemoryProvider

    assert ProviderConfig is not None
    assert MetronixClient is not None
    assert MetronixMemoryProvider is not None


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
