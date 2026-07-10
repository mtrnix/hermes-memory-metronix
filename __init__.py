from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hermes_memory_metronix import MetronixMemoryProvider


def register(ctx) -> None:
    ctx.register_memory_provider(MetronixMemoryProvider())
