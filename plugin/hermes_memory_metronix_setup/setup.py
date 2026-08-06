"""Interactive, opt-in setup for the PyPI-distributed Hermes plugin."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path


def packaged_plugin_dir() -> Path:
    """Return the provider package bundled in the installed distribution."""
    return Path(__file__).resolve().parent.parent / "metronix"


def install_plugin(source: Path, destination: Path, *, force: bool = False) -> None:
    """Copy the packaged provider to Hermes's user plugin directory."""
    if destination.exists() or destination.is_symlink():
        if not force:
            raise FileExistsError(
                f"{destination} already exists; rerun with --force to replace it"
            )
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def _require_single_line(value: str, name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} is required")
    if "\n" in cleaned or "\r" in cleaned:
        raise ValueError(f"{name} must be a single line")
    return cleaned


def _atomic_write(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
        os.chmod(path, mode)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"cannot read existing configuration at {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"configuration at {path} must be a JSON object")
    return value


def _upsert_env_value(content: str, key: str, value: str) -> str:
    replacement = f"{key}={value}"
    lines = content.splitlines()
    result: list[str] = []
    replaced = False
    for line in lines:
        candidate = line.removeprefix("export ")
        if candidate.startswith(f"{key}="):
            if not replaced:
                result.append(replacement)
                replaced = True
            continue
        result.append(line)
    if not replaced:
        result.append(replacement)
    return "\n".join(result) + "\n"


def write_configuration(
    hermes_home: Path,
    *,
    base_url: str,
    workspace_id: str,
    auth_token: str,
) -> None:
    """Persist non-secrets and a REST token to Hermes-owned private files."""
    base_url = _require_single_line(base_url, "base URL").rstrip("/")
    workspace_id = _require_single_line(workspace_id, "workspace ID")
    auth_token = _require_single_line(auth_token, "auth token")

    config_path = hermes_home / "metronix.json"
    config = _read_json_object(config_path)
    config.update({"base_url": base_url, "workspace_id": workspace_id})
    _atomic_write(config_path, json.dumps(config, indent=2) + "\n", 0o600)

    env_path = hermes_home / ".env"
    existing_env = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    _atomic_write(env_path, _upsert_env_value(existing_env, "METRONIX_AUTH_TOKEN", auth_token), 0o600)


def _default_hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install and securely configure the Metronix Hermes memory provider."
    )
    parser.add_argument(
        "--hermes-home",
        type=Path,
        default=_default_hermes_home(),
        help="Hermes configuration directory (default: $HERMES_HOME or ~/.hermes)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing ~/.hermes/plugins/metronix installation",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    run_command: Callable[[list[str]], object] | None = None,
    input_func: Callable[[str], str] = input,
    secret_func: Callable[[str], str] = getpass.getpass,
) -> int:
    """Install the provider, collect an existing REST token, and activate it."""
    args = _parse_args(argv)
    hermes_home = args.hermes_home.expanduser()

    print("Metronix needs a REST JWT or mtk_ personal key for /api/v1/*.")
    print("Do not enter METRONIX_MCP_API_KEY here. The token will not be displayed.")
    base_url = input_func("Metronix base URL: ")
    workspace_id = input_func("Metronix workspace ID: ")
    auth_token = secret_func("Metronix REST token: ")

    try:
        install_plugin(packaged_plugin_dir(), hermes_home / "plugins" / "metronix", force=args.force)
        write_configuration(
            hermes_home,
            base_url=base_url,
            workspace_id=workspace_id,
            auth_token=auth_token,
        )
    except (FileExistsError, OSError, ValueError) as error:
        print(f"Setup did not complete: {error}")
        return 1

    command = ["hermes", "memory", "setup", "metronix"]
    try:
        if run_command is None:
            subprocess.run(command, check=True)
        else:
            run_command(command)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Configuration was saved, but Hermes activation failed: {error}")
        print("Run this command after resolving the Hermes error: hermes memory setup metronix")
        return 1

    print(f"Saved configuration to {hermes_home / 'metronix.json'} and {hermes_home / '.env'}.")
    print("Keep the original token in a password manager and rotate it if it is exposed.")
    print("Next: run 'hermes memory status', then start a normal 'hermes chat'.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
