#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip || true
if ! python -m pip install -e .; then
  echo "[WARN] normal editable install failed; retrying without build isolation/deps"
  python -m pip install -e . --no-build-isolation --no-deps
fi
