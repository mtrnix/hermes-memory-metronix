# hermes-memory-metronix

Standalone Hermes `MemoryProvider` backed by Metronix Memory.

This repository owns the Hermes-native adapter layer:

- Hermes plugin packaging
- config and auth resolution
- prefetch and write-through behavior
- Hermes-focused unit, integration, and smoke tests

Metronix backend contracts and MCP integration docs remain in the
`metronix-memory` repository.

## Development

Run the fast local checks:

```bash
python3 -m pytest tests/unit -v
RUN_INTEGRATION_TESTS=1 python3 -m pytest tests/integration/test_live_metronix.py -v
```
