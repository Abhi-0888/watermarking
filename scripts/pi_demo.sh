#!/usr/bin/env bash
# scripts/pi_demo.sh — Activate the venv and run the full Pi integration demo.
#
# Usage (from project root):
#   bash scripts/pi_demo.sh               # plain-print mode
#   bash scripts/pi_demo.sh --fullscreen  # curses kiosk display
#   bash scripts/pi_demo.sh --no-led      # skip GPIO (bench/laptop testing)
#   bash scripts/pi_demo.sh --skip-issue  # files already generated
#   bash scripts/pi_demo.sh --skip-tamper # skip tamper variants
#
# All extra flags are forwarded to pi_demo.py.
# The script must be run from the project root (SecureDocSystem/).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_ACTIVATE="$PROJECT_ROOT/venv/bin/activate"

# ── Activate venv if present ──────────────────────────────────────────────────
if [ -f "$VENV_ACTIVATE" ]; then
    # shellcheck source=/dev/null
    source "$VENV_ACTIVATE"
    echo "[pi_demo.sh] venv activated: $VENV_ACTIVATE"
else
    echo "[pi_demo.sh] WARNING: venv not found at $VENV_ACTIVATE"
    echo "             Running with system Python. Run setup first:"
    echo "               python3 -m venv --system-site-packages venv"
    echo "               source venv/bin/activate"
    echo "               pip install -r requirements.txt"
    echo "               bash raspberry_pi/install_gpio.sh"
fi

# ── Run the integration demo ──────────────────────────────────────────────────
cd "$PROJECT_ROOT"
echo "[pi_demo.sh] Running: python3 scripts/pi_demo.py $*"
echo ""
python3 scripts/pi_demo.py "$@"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "[pi_demo.sh] Demo completed successfully (authentic copy verified ✓)."
else
    echo "[pi_demo.sh] Demo finished with exit code $EXIT_CODE." >&2
    echo "             Check the output above for TAMPERED / ERROR verdicts." >&2
fi

exit $EXIT_CODE
