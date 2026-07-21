# PyPI Trusted Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `hermes-memory-metronix` `0.1.1` to PyPI through GitHub OIDC Trusted Publishing, with verified wheel and source artifacts.

**Architecture:** `pyproject.toml` owns release metadata. A release-only workflow builds and validates artifacts, transfers them to a protected OIDC upload job, and publishes to PyPI. GitHub installation remains the Hermes setup path.

**Tech Stack:** Python 3.11+, uv, setuptools, pytest, twine, GitHub Actions, `pypa/gh-action-pypi-publish@release/v1`.

## Global Constraints

- Release `0.1.1`; never overwrite `v0.1.0`.
- Do not add a PyPI API token, `.pypirc`, or publishing secret.
- Only `.github/workflows/pypi-publish.yml` publishes, through environment `pypi`.
- Only the PyPI upload job receives `id-token: write`.
- Keep `hermes plugins install mtrnix/hermes-memory-metronix --no-enable` as the supported Hermes installation command.
- Build and validate both wheel and source distribution before upload.

---

### Task 1: Define the `0.1.1` distribution contract

**Files:**
- Modify: `pyproject.toml`, `README.md`
- Create: `tests/unit/test_release_metadata.py`

**Interfaces:** Consumes PEP 621 metadata and produces discoverable PyPI metadata plus documentation that distinguishes distribution from Hermes installation.

- [ ] **Step 1: Write failing tests**

```python
def test_pypi_release_metadata_is_complete() -> None:
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    assert project["version"] == "0.1.1"
    assert project["urls"]["Repository"] == "https://github.com/mtrnix/hermes-memory-metronix"
    assert project["urls"]["Issues"] == "https://github.com/mtrnix/hermes-memory-metronix/issues"
    assert "Programming Language :: Python :: 3" in project["classifiers"]

def test_readme_keeps_git_plugin_install_as_the_hermes_path() -> None:
    assert "hermes plugins install mtrnix/hermes-memory-metronix --no-enable" in readme
    assert "does not register the provider with Hermes" in readme
```

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev pytest tests/unit/test_release_metadata.py -q`

Expected: failure because metadata is `0.1.0` and the README lacks the PyPI boundary.

- [ ] **Step 3: Implement metadata and documentation**

Set `version = "0.1.1"`; add `[project.urls]` for Repository and Issues; add classifiers for Python 3, Python 3 only, Python 3.11, Apache Software License, and OS Independent. Add:

```markdown
## Python distribution

`pip install hermes-memory-metronix` distributes the adapter for development
and Hermes-hosted environments. It does not register the provider with Hermes;
use the GitHub plugin installation command above for Hermes discovery.
```

- [ ] **Step 4: Verify GREEN and commit**

Run: `uv run --extra dev pytest tests/unit/test_release_metadata.py -q`

Expected: `2 passed`.

```bash
git add pyproject.toml README.md tests/unit/test_release_metadata.py
git commit -m "chore: prepare PyPI release metadata"
```

### Task 2: Validate distribution artifacts in CI

**Files:** Modify `.github/workflows/ci.yml`.

**Interfaces:** Consumes `uv build` output and produces CI evidence that both distribution types have valid metadata.

- [ ] **Step 1: Verify the pre-change artifact check fails**

```bash
build_dir=$(mktemp -d /private/tmp/hermes-memory-metronix-build.XXXXXX)
uv build --out-dir "$build_dir"
uv run --with twine twine check "$build_dir"/*
BUILD_DIR="$build_dir" python -c 'from pathlib import Path; import os; files = list(Path(os.environ["BUILD_DIR"]).glob("hermes_memory_metronix-0.1.1*")); assert len(files) == 2, files'
```

Expected: failure before Task 1 because no `0.1.1` files exist.

- [ ] **Step 2: Add CI validation**

Append this step after the Hermes contract suite:

```yaml
      - name: Build and validate distribution artifacts
        run: |
          uv build
          uv run --with twine twine check dist/*
          python -c 'from pathlib import Path; files = list(Path("dist").glob("*.whl")) + list(Path("dist").glob("*.tar.gz")); assert len(files) == 2, files'
```

- [ ] **Step 3: Verify GREEN and commit**

Run the Task 2 build command above after Task 1; expect `twine check` passes for one wheel and one source distribution.

```bash
git add .github/workflows/ci.yml
git commit -m "ci: validate PyPI distribution artifacts"
```

### Task 3: Add release-only OIDC publishing

**Files:** Create `.github/workflows/pypi-publish.yml`.

**Interfaces:** Consumes a published GitHub Release and the configured pending publisher; produces a PyPI upload with a short-lived OIDC credential.

- [ ] **Step 1: Create the workflow**

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.release.tag_name }}
      - uses: astral-sh/setup-uv@v6
      - name: Build and validate distributions
        run: |
          uv build
          uv run --with twine twine check dist/*
      - uses: actions/upload-artifact@v4
        with:
          name: python-distributions
          path: dist/
  publish-to-pypi:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/hermes-memory-metronix
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: python-distributions
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 2: Verify workflow policy and commit**

Run: `rg -n 'types: \[published\]|id-token: write|name: pypi|gh-action-pypi-publish@release/v1' .github/workflows/pypi-publish.yml`

Expected: all controls are present and no `PYPI_TOKEN` or `TWINE_PASSWORD` appears.

```bash
git add .github/workflows/pypi-publish.yml
git commit -m "ci: publish releases to PyPI with OIDC"
```

### Task 4: Review, release, and verify

**Files:** Verify GitHub PR, GitHub Release `v0.1.1`, and PyPI project.

- [ ] Push the branch, open a draft PR, and wait for CI including artifact validation.
- [ ] Merge the approved PR.
- [ ] Create GitHub Release `v0.1.1`; it triggers the PyPI workflow once.
- [ ] Verify the release with:

```bash
verify_dir=$(mktemp -d /private/tmp/hermes-memory-metronix-pypi-verify.XXXXXX)
python -m venv "$verify_dir"
"$verify_dir/bin/python" -m pip install --upgrade pip
"$verify_dir/bin/python" -m pip install hermes-memory-metronix==0.1.1
"$verify_dir/bin/python" -c 'from importlib.metadata import version; assert version("hermes-memory-metronix") == "0.1.1"'
```

Expected: PyPI serves `0.1.1`; installed metadata reports `0.1.1`.
