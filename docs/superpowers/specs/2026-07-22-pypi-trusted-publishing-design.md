# PyPI Trusted Publishing Design

## Goal

Publish `hermes-memory-metronix` `0.1.1` to PyPI through GitHub Actions
Trusted Publishing, without storing a PyPI API token.

## Scope

`v0.1.0` is an immutable GitHub release. The PyPI workflow and metadata ship
in a new `v0.1.1` release.

PyPI distributes the Python adapter for development and Hermes-hosted
environments. It does not replace the supported Hermes installation:

```bash
hermes plugins install mtrnix/hermes-memory-metronix --no-enable
```

Hermes discovery needs the repository plugin layout (`__init__.py`,
`plugin.yaml`, and `plugin/metronix/`), so documentation must not claim that
`pip install` alone registers a provider.

## Distribution metadata and validation

`pyproject.toml` remains the only version source. Version `0.1.1` adds public
repository/issue URLs and classifiers consistent with Python 3.11+ and the
Apache-2.0 license. The build creates a wheel and source distribution with
`uv build`; `twine check` validates both. A clean environment verifies the
installed distribution metadata without importing `metronix` outside a Hermes
host, where `agent.memory_provider` is intentionally supplied by Hermes.

## Release workflow

`.github/workflows/pypi-publish.yml` runs only when a GitHub Release is
published. Its build job checks out that release tag, builds and validates
artifacts, and uploads them as a GitHub artifact. The publish job downloads
that artifact, uses the protected `pypi` environment, and has the only
`id-token: write` permission. It publishes with
`pypa/gh-action-pypi-publish@release/v1`.

The configured PyPI pending publisher is bound to repository
`mtrnix/hermes-memory-metronix`, workflow `pypi-publish.yml`, and environment
`pypi`. No API token, `.pypirc`, or publishing secret is added.

## Failure handling

PyPI versions are immutable. If publishing fails, diagnose the release
workflow or Trusted Publisher configuration and issue a new patch release;
never reuse or overwrite `v0.1.1`.

## Non-goals

- No PyPI-driven Hermes registration or installer CLI.
- No Metronix backend or Hermes-core change.
