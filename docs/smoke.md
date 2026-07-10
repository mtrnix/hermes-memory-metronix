# Hermes Smoke

## Environment

- `METRONIX_BASE_URL`
- `METRONIX_WORKSPACE_ID`
- `METRONIX_AUTH_TOKEN`
- optional `METRONIX_AGENT_ID`

## Verify plugin

```bash
python -m pytest tests/unit -v
RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_live_metronix.py -v
```

## Verify Hermes

1. Install the plugin into `~/.hermes/plugins/metronix`.
2. Export the Metronix REST environment variables in the Hermes shell.
3. Run `hermes chat --memory-provider metronix`.
4. Ask one question that should retrieve prior memory.
5. Ask a second question that should write new memory.
6. Verify the memory was written back under the active Hermes agent id.
