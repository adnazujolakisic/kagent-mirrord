#!/bin/bash
# Run research-crew locally under mirrord with the right Python + deps.
# kagent-crewai needs Python >= 3.10 (avoid macOS /usr/bin/python3 == 3.9).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="$ROOT/.venv"
PY="$VENV/bin/python3"

pick_python3() {
  local c
  # Prefer 3.12/3.11 (closer to crew/Dockerfile 3.11) before newer Pythons.
  for c in python3.12 python3.11 python3.10 python3.13 python3.14 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

PY_BOOTSTRAP="$(pick_python3)" || {
  echo "Need Python 3.10+ for kagent-crewai. Install e.g. brew install python@3.12 and ensure python3.12 is on PATH."
  exit 1
}

if [ -x "$PY" ] && ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "==> Removing .venv (was built with Python < 3.10; kagent-crewai requires 3.10+) ..."
  rm -rf "$VENV"
fi

if [ ! -x "$PY" ]; then
  echo "==> Creating .venv with $PY_BOOTSTRAP ..."
  "$PY_BOOTSTRAP" -m venv "$VENV"
fi

if ! "$PY" -c "import kagent" 2>/dev/null; then
  echo "==> Installing deps with uv (pip hits resolution-too-deep on crewai+kagent-crewai; first run ~1-2 min) ..."
  if ! curl -sf --max-time 20 -o /dev/null "https://pypi.org/simple/"; then
    echo "Cannot reach PyPI (https://pypi.org). uv/pip need working DNS and outbound HTTPS."
    echo "Try: fix Wi-Fi, pause VPN or enable split tunneling, set DNS to 1.1.1.1 or 8.8.8.8, then retry."
    echo "If you see 'dns error' / 'nodename nor servname', this is a local network/DNS issue, not the repo."
    exit 1
  fi
  "$PY" -m pip install -q uv
  "$PY" -m uv pip install -r requirements-local.txt --python "$PY"
fi

exec mirrord exec -f mirrord/research-crew.json -- "$PY" crew/main.py
