# Hermes Smoke

## Quick setup

Install and configure the provider first:

```bash
python3 -m pip install --upgrade "hermes-memory-metronix>=0.1.3"
hermes-metronix-setup
```

Until v0.1.3 is published, use the repository install script from the README.

The setup command securely stores a REST JWT or personal API key. Do not use
`METRONIX_MCP_API_KEY` for the provider.

## Verify plugin

```bash
uv run --extra dev pytest tests/unit -v
RUN_INTEGRATION_TESTS=1 uv run --extra dev pytest tests/integration/test_live_metronix.py -v
```

## Verify Hermes

1. Verify the real Hermes API before installation:

   ```bash
   HERMES_AGENT_SRC=/absolute/path/to/hermes-agent \
     uv run --extra dev pytest \
     tests/unit/test_real_abc_contract.py tests/unit/test_hermes_plugin.py -v
   ```

2. Run `hermes memory status` and confirm it shows `Provider: metronix`.
3. Run `hermes chat`.
4. Store a unique fact, exit, and start a fresh `hermes chat` session.
5. Ask for that fact and verify that it is retrieved.
