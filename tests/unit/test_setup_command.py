from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_memory_metronix_setup import setup


def _source_plugin(tmp_path: Path) -> Path:
    source = tmp_path / "source" / "metronix"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text("PLUGIN = True\n", encoding="utf-8")
    return source


def test_install_plugin_copies_packaged_provider(tmp_path: Path) -> None:
    source = _source_plugin(tmp_path)
    destination = tmp_path / ".hermes" / "plugins" / "metronix"

    setup.install_plugin(source, destination)

    assert (destination / "__init__.py").read_text(encoding="utf-8") == "PLUGIN = True\n"


def test_install_plugin_refuses_to_replace_existing_provider(tmp_path: Path) -> None:
    source = _source_plugin(tmp_path)
    destination = tmp_path / ".hermes" / "plugins" / "metronix"
    destination.mkdir(parents=True)

    with pytest.raises(FileExistsError, match="--force"):
        setup.install_plugin(source, destination)


def test_configure_writes_private_secret_file_and_preserves_other_entries(tmp_path: Path) -> None:
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    env_file = hermes_home / ".env"
    env_file.write_text("OTHER_SETTING=keep\nMETRONIX_AUTH_TOKEN=old\n", encoding="utf-8")

    setup.write_configuration(
        hermes_home,
        base_url="https://memory.example",
        workspace_id="TEST",
        auth_token="new-token",
    )

    assert (hermes_home / "metronix.json").read_text(encoding="utf-8") == (
        '{\n  "base_url": "https://memory.example",\n  "workspace_id": "TEST"\n}\n'
    )
    assert env_file.read_text(encoding="utf-8") == (
        "OTHER_SETTING=keep\nMETRONIX_AUTH_TOKEN=new-token\n"
    )
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600


def test_configure_rejects_multiline_secret(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="single line"):
        setup.write_configuration(
            tmp_path / ".hermes",
            base_url="https://memory.example",
            workspace_id="TEST",
            auth_token="token\nleak",
        )


def test_create_rest_token_uses_curl_without_exposing_credentials() -> None:
    commands: list[tuple[list[str], str]] = []
    curl_configs: list[str] = []
    responses = iter(
        [
            '{"token":"login-jwt","user_id":"user-123"}',
            '{"raw_key":"mtk_generated_token"}',
        ]
    )

    def run_curl(command: list[str], payload: str) -> subprocess.CompletedProcess[str]:
        commands.append((command, payload))
        config_path = Path(command[command.index("--config") + 1])
        curl_configs.append(config_path.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(command, 0, next(responses), "")

    token = setup.create_rest_token_with_curl(
        "https://memory.example/",
        email="demo@example.com",
        password="correct-horse-battery-staple",
        run_curl=run_curl,
    )

    assert token == "mtk_generated_token"
    assert [payload for _, payload in commands] == [
        '{"email":"demo@example.com","password":"correct-horse-battery-staple"}',
        "",
    ]
    assert all("correct-horse-battery-staple" not in part for command, _ in commands for part in command)
    assert all("login-jwt" not in part for command, _ in commands for part in command)
    assert curl_configs == [
        'url = "https://memory.example/api/v1/auth/login"\nrequest = "POST"\nheader = "Content-Type: application/json"\n',
        'url = "https://memory.example/api/v1/users/user-123/api-keys"\nrequest = "POST"\nheader = "Authorization: Bearer login-jwt"\n',
    ]


def test_main_activates_provider_after_persisting_configuration(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = _source_plugin(tmp_path)
    commands: list[list[str]] = []
    answers = iter(["https://memory.example", "TEST"])
    monkeypatch.setattr(setup, "packaged_plugin_dir", lambda: source)

    exit_code = setup.main(
        [
            "--hermes-home",
            str(tmp_path / ".hermes"),
        ],
        run_command=lambda command: commands.append(command),
        input_func=lambda prompt: next(answers),
        secret_func=lambda prompt: "test-token",
    )

    assert exit_code == 0
    assert commands == [["hermes", "memory", "setup", "metronix"]]


def test_main_generates_and_persists_a_rest_token_with_curl(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = _source_plugin(tmp_path)
    answers = iter(["https://memory.example", "TEST", "demo@example.com"])
    curl_payloads: list[str] = []
    responses = iter(
        [
            '{"token":"login-jwt","user_id":"user-123"}',
            '{"raw_key":"mtk_generated_token"}',
        ]
    )
    monkeypatch.setattr(setup, "packaged_plugin_dir", lambda: source)

    def run_curl(command: list[str], payload: str) -> subprocess.CompletedProcess[str]:
        curl_payloads.append(payload)
        return subprocess.CompletedProcess(command, 0, next(responses), "")

    hermes_home = tmp_path / ".hermes"
    exit_code = setup.main(
        ["--hermes-home", str(hermes_home), "--generate-token"],
        run_command=lambda command: None,
        run_curl=run_curl,
        input_func=lambda prompt: next(answers),
        secret_func=lambda prompt: "demo-password",
    )

    assert exit_code == 0
    assert curl_payloads == ['{"email":"demo@example.com","password":"demo-password"}', ""]
    assert (hermes_home / ".env").read_text(encoding="utf-8") == (
        "METRONIX_AUTH_TOKEN=mtk_generated_token\n"
    )


def test_setup_helper_imports_without_hermes_agent() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from hermes_memory_metronix_setup import setup; print(setup.packaged_plugin_dir().name)",
        ],
        cwd=root,
        env={"PYTHONPATH": str(root / "plugin")},
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "metronix"
