from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_PLUGIN = _ROOT / "plugin"
if str(_PLUGIN) not in sys.path:
    sys.path.insert(0, str(_PLUGIN))

from metronix import MetronixMemoryProvider


def register(ctx) -> None:
    ctx.register_memory_provider(MetronixMemoryProvider())
