from __future__ import annotations

from threading import Lock
from typing import Any
import json
from pathlib import Path

from agent.memory_provider import MemoryProvider

from .client import MetronixClient
from .config import ProviderConfig


class MetronixMemoryProvider(MemoryProvider):
    def __init__(
        self,
        *,
        config: ProviderConfig | None = None,
        client: MetronixClient | None = None,
        runtime_agent_id: str | None = None,
    ) -> None:
        self._config = config or ProviderConfig.from_hermes()
        self._client = client or MetronixClient(
            base_url=self._config.base_url,
            auth_token=self._config.auth_token,
        )
        self._runtime_agent_id = runtime_agent_id
        self._session_id = ""
        self._prefetch_cache: dict[str, str] = {}
        self._lock = Lock()

    @property
    def name(self) -> str:
        return "metronix"

    def is_available(self) -> bool:
        return bool(self._config.base_url and self._config.workspace_id and self._config.auth_token)

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        self._session_id = session_id
        runtime_agent_id = kwargs.get("agent_identity")
        if runtime_agent_id:
            self._runtime_agent_id = str(runtime_agent_id)

    def _agent_id(self) -> str:
        return self._config.resolve_agent_id(self._runtime_agent_id)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return []

    def get_config_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "key": "base_url",
                "description": "Metronix base URL",
                "required": True,
                "env_var": "METRONIX_BASE_URL",
            },
            {
                "key": "workspace_id",
                "description": "Metronix workspace ID",
                "required": True,
                "env_var": "METRONIX_WORKSPACE_ID",
            },
            {
                "key": "auth_token",
                "description": "Metronix REST auth token",
                "secret": True,
                "required": True,
                "env_var": "METRONIX_AUTH_TOKEN",
            },
            {
                "key": "prefetch_top_k",
                "description": "Maximum records to inject during prefetch",
                "default": "5",
                "env_var": "METRONIX_PREFETCH_TOP_K",
            },
            {
                "key": "write_through",
                "description": "Mirror built-in Hermes memory writes into Metronix",
                "default": "true",
                "choices": ["true", "false"],
                "env_var": "METRONIX_WRITE_THROUGH",
            },
            {
                "key": "write_scope",
                "description": "Write scope label stored with Hermes memory writes",
                "default": "workspace",
                "choices": ["workspace", "shared", "profile"],
                "env_var": "METRONIX_WRITE_SCOPE",
            },
        ]

    def save_config(self, values: dict[str, Any], hermes_home: str) -> None:
        payload = {
            "base_url": values.get("base_url", ""),
            "workspace_id": values.get("workspace_id", ""),
            "prefetch_top_k": int(values.get("prefetch_top_k", 5)),
            "write_through": str(values.get("write_through", "true")).lower() not in {"0", "false", "no", "off"},
            "write_scope": values.get("write_scope", "workspace"),
        }
        config_path = Path(hermes_home) / "metronix.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(payload, indent=2) + "\n")

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        with self._lock:
            return self._prefetch_cache.get(session_id, "")

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        if not self._config.prefetch_enabled:
            return
        try:
            result = self._client.search_memory(
                workspace_id=self._config.workspace_id,
                agent_id=self._agent_id(),
                query=query,
                top_k=self._config.prefetch_top_k,
            )
            formatted = "\n".join(record["content"] for record in result.get("records", []))
        except Exception:
            formatted = ""
        with self._lock:
            self._session_id = session_id
            self._prefetch_cache[session_id] = formatted

    def on_memory_add(self, content: str, *, memory_type: str = "fact") -> None:
        if not self._config.write_through:
            return
        try:
            self._client.store_memory(
                workspace_id=self._config.workspace_id,
                agent_id=self._agent_id(),
                content=content,
                memory_type=memory_type,
            )
        except Exception:
            return

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        del metadata
        if action not in {"add", "replace"} or not content:
            return
        self.on_memory_add(content, memory_type=target)

    def on_session_switch(
        self,
        new_session_id,
        *,
        parent_session_id="",
        reset=False,
        rewound=False,
        **kwargs,
    ):
        old_session_id = self._session_id
        self._session_id = new_session_id
        with self._lock:
            if old_session_id:
                self._prefetch_cache.pop(old_session_id, None)
