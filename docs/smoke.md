# Hermes Smoke

## Quick setup

```bash
python3 -m pip install --upgrade "hermes-memory-metronix>=2026.32.2"
hermes-metronix-setup
```

The setup command stores a REST JWT or `mtk_…` personal key securely.
`mtk_…` keys require Metronix core's shared REST authentication resolver. Do
not use `METRONIX_MCP_API_KEY` for the provider.

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
3. Run `hermes chat`, store a unique fact, then start a fresh chat session.
4. Ask for that fact and verify it is retrieved.
