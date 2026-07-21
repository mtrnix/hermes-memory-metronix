from __future__ import annotations

import os

import pytest

from metronix.client import MetronixClient


@pytest.mark.integration
def test_live_store_search_delete_smoke() -> None:
    if not os.environ.get("RUN_INTEGRATION_TESTS"):
        pytest.skip("set RUN_INTEGRATION_TESTS=1 for live Metronix verification")

    base_url = os.environ["METRONIX_BASE_URL"]
    token = os.environ["METRONIX_AUTH_TOKEN"]
    workspace_id = os.environ["METRONIX_WORKSPACE_ID"]
    agent_id = os.environ["METRONIX_AGENT_ID"]

    client = MetronixClient(
        base_url=base_url,
        workspace_id=workspace_id,
        auth_token=token,
    )
    result = client.search_memory(query="smoke", top_k=1, agent_id=agent_id)
    assert isinstance(result, list)
