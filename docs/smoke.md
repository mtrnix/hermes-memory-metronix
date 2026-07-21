# Hermes Smoke

## Environment

- `METRONIX_BASE_URL`
- `METRONIX_WORKSPACE_ID`
- `METRONIX_AUTH_TOKEN`
- optional `METRONIX_AGENT_ID`

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

2. Install the plugin into `~/.hermes/plugins/metronix`.
3. Export Metronix REST credentials (`METRONIX_AUTH_TOKEN`, or email and
   password) in the Hermes shell. Do not use `METRONIX_MCP_API_KEY` here.
4. Run `hermes chat --memory-provider metronix`.
5. Ask one question that should retrieve prior memory.
6. Ask a second question that should write new memory.
7. Verify the memory was written back under the active Hermes agent id.
