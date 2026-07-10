from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _strip_mcp_suffix(url: str) -> str:
    clean = url.rstrip("/")
    if clean.endswith("/mcp"):
        return clean[:-4]
    return clean


@dataclass(slots=True)
class ProviderConfig:
    base_url: str
    workspace_id: str
    auth_token: str | None = None
    email: str | None = None
    password: str | None = None
    agent_id_override: str | None = None
    prefetch_enabled: bool = True
    prefetch_top_k: int = 5
    write_through: bool = True
    write_scope: str = "workspace"

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        return cls(
            base_url=os.environ["METRONIX_BASE_URL"].rstrip("/"),
            workspace_id=os.environ["METRONIX_WORKSPACE_ID"],
            auth_token=os.environ.get("METRONIX_AUTH_TOKEN"),
            email=os.environ.get("METRONIX_EMAIL"),
            password=os.environ.get("METRONIX_PASSWORD"),
            agent_id_override=os.environ.get("METRONIX_AGENT_ID"),
            prefetch_enabled=_env_flag("METRONIX_PREFETCH", True),
            prefetch_top_k=int(os.environ.get("METRONIX_PREFETCH_TOP_K", "5")),
            write_through=_env_flag("METRONIX_WRITE_THROUGH", True),
            write_scope=os.environ.get("METRONIX_WRITE_SCOPE", "workspace"),
        )

    @classmethod
    def from_hermes(cls, hermes_home: str | None = None) -> "ProviderConfig":
        base_home = Path(hermes_home).expanduser() if hermes_home else Path.home() / ".hermes"
        config_path = base_home / "metronix.json"
        payload: dict[str, object] = {}
        if config_path.exists():
            payload = json.loads(config_path.read_text())

        raw_base_url = (
            os.environ.get("METRONIX_BASE_URL")
            or str(payload.get("base_url", ""))
            or os.environ.get("METRONIX_URL", "")
        )
        base_url = _strip_mcp_suffix(raw_base_url)
        workspace_id = (
            os.environ.get("METRONIX_WORKSPACE_ID")
            or str(payload.get("workspace_id", ""))
            or os.environ.get("DEFAULT_WORKSPACE_ID", "")
        )
        auth_token = os.environ.get("METRONIX_AUTH_TOKEN", str(payload.get("auth_token", "")) or None)
        email = os.environ.get("METRONIX_EMAIL", str(payload.get("email", "")) or None)
        password = os.environ.get("METRONIX_PASSWORD", str(payload.get("password", "")) or None)
        agent_id_override = (
            os.environ.get("METRONIX_AGENT_ID")
            or str(payload.get("agent_id_override", payload.get("agent_id", ""))) or None
            or os.environ.get("AGENT_UUID")
        )
        prefetch_enabled = _env_flag(
            "METRONIX_PREFETCH",
            bool(payload.get("prefetch_enabled", payload.get("prefetch", True))),
        )
        prefetch_top_k = int(
            os.environ.get(
                "METRONIX_PREFETCH_TOP_K",
                str(payload.get("prefetch_top_k", 5)),
            )
        )
        write_through = _env_flag(
            "METRONIX_WRITE_THROUGH",
            bool(payload.get("write_through", True)),
        )
        write_scope = os.environ.get(
            "METRONIX_WRITE_SCOPE",
            str(payload.get("write_scope", "workspace")),
        )

        return cls(
            base_url=base_url,
            workspace_id=workspace_id,
            auth_token=auth_token,
            email=email,
            password=password,
            agent_id_override=agent_id_override,
            prefetch_enabled=prefetch_enabled,
            prefetch_top_k=prefetch_top_k,
            write_through=write_through,
            write_scope=write_scope,
        )

    def resolve_agent_id(self, runtime_agent_id: str | None) -> str:
        if self.agent_id_override:
            return self.agent_id_override
        if runtime_agent_id:
            return runtime_agent_id
        raise ValueError("A runtime Hermes agent identity or METRONIX_AGENT_ID is required")
