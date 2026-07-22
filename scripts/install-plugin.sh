#!/usr/bin/env bash
# Install the latest provider source, then run its interactive, secure setup command.
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install Python 3, then run this script again." >&2
  exit 1
fi

python3 -m pip install --upgrade \
  "git+https://github.com/mtrnix/hermes-memory-metronix.git@main"
exec hermes-metronix-setup "$@"
