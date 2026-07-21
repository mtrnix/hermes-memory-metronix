from __future__ import annotations

from pathlib import Path
import tomllib


def test_pypi_release_metadata_and_installation_guidance() -> None:
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    readme = (root / "README.md").read_text()

    assert project["version"] == "0.1.1"
    assert project["license"] == "Apache-2.0"
    assert project["urls"] == {
        "Repository": "https://github.com/mtrnix/hermes-memory-metronix",
        "Issues": "https://github.com/mtrnix/hermes-memory-metronix/issues",
    }
    assert "Programming Language :: Python :: 3" in project["classifiers"]
    assert "hermes plugins install mtrnix/hermes-memory-metronix --no-enable" in readme
    assert "does not register the provider with Hermes" in readme
