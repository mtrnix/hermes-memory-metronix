from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(slots=True)
class MetronixClient:
    base_url: str
    auth_token: str | None = None

    def _headers(self) -> dict[str, str]:
        if not self.auth_token:
            raise ValueError("REST auth is required")
        return {"Authorization": f"Bearer {self.auth_token}"}

    def search_memory(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        query: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        response = requests.request(
            "POST",
            f"{self.base_url}/api/v1/memory/search?workspace_id={workspace_id}",
            headers=self._headers(),
            json={"query": query, "agent_id": agent_id, "top_k": top_k},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def store_memory(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        content: str,
        memory_type: str,
    ) -> dict[str, Any]:
        response = requests.request(
            "POST",
            f"{self.base_url}/api/v1/memory/records?workspace_id={workspace_id}",
            headers=self._headers(),
            json={
                "agent_id": agent_id,
                "content": content,
                "scope": "PER_AGENT",
                "kind": memory_type,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def delete_memory(self, *, workspace_id: str, memory_id: str) -> dict[str, Any]:
        response = requests.request(
            "DELETE",
            f"{self.base_url}/api/v1/memory/records/{memory_id}?workspace_id={workspace_id}",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
