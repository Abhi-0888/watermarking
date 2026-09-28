#!/usr/bin/env bash
# =============================================================================
# scripts/pi_deploy.sh
# Run from your LAPTOP (not the Pi) from the project root.
#
# What it does (end to end):
#   1. Checks SSH connectivity to 10.1.14.11
#   2. Transfers the full project to the Pi (excluding private keys and venv)
#   3. Transfers generated sample files (watermarked.png, manifests, etc.)
#   4. Creates venv and installs Python dependencies on the Pi
#   5. Installs the correct GPIO library (rpi-lgpio for Pi 5, RPi.GPIO otherwise)
#   6. Runs a quick smoke-test verification on the Pi
#
# Prerequisites:
#   - SSH enabled on the Pi (run scripts/pi_ssh_setup.sh in VNC terminal first)
#   - OpenSSH client on Windows (comes with Windows 10/11 or Git Bash)
#   - Generated sample files: run `py -3 scripts/pi_demo.py --no-led` first
#
# Usage:
#   bash scripts/pi_deploy.sh                    # full deploy + verify
#   bash scripts/pi_deploy.sh --skip-transfer    # only run verify (files exist)
#   bash scripts/pi_deploy.sh --skip-setup       # skip venv/pip, only transfer
# =============================================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
PI_HOST="10.1.14.11"
PI_USER="fun"
PI_PORT="22"
PI_DIR="/home/fun/SecureDocSystem"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o BatchMode=yes"
SSH="ssh -p $PI_PORT $SSH_OPTS $PI_USER@$PI_HOST"
SCP="scp -P $PI_PORT $SSH_OPTS"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SKIP_TRANSFER=false
SKIP_SETUP=false
for arg in "$@"; do
    case "$arg" in
        --skip-transfer) SKIP_TRANSFER=true ;;
        --skip-setup)    SKIP_SETUP=true ;;
    esac
done

echo "========================================================"
echo "  SecureDocSystem — Pi Deployment"
echo "  Target : $PI_USER@$PI_HOST:$PI_DIR"
echo "========================================================"

# ── Step 1: Check SSH ─────────────────────────────────────────────────────────
echo ""
echo "[1] Checking SSH connectivity..."
if ! $SSH "echo SSH_OK" 2>/dev/null | grep -q "SSH_OK"; then
    echo ""
    echo "  ERROR: Cannot connect to $PI_USER@$PI_HOST on port $PI_PORT"
    echo ""
    echo "  The Pi is reachable by ping but SSH is not responding."
    echo "  You need to enable SSH first. Steps:"
    echo ""
    echo "  1. Open RealVNC Viewer → connect to 10.1.14.11"
    echo "     Catchphrase : Audio neon fossil. Ticket Gong Ringo."
    echo "     (Click 'I have a catchphrase' if prompted)"
    echo ""
    echo "  2. In the VNC desktop, open a Terminal and run:"
    echo "     bash ~/pi_ssh_setup.sh"
    echo ""
    echo "  3. If pi_ssh_setup.sh is not on the Pi yet, type this directly:"
    echo "     sudo systemctl enable ssh && sudo systemctl start ssh"
    echo ""
    echo "  4. Then re-run this script."
    exit 1
fi
echo "  SSH OK ✓  ($PI_USER@$PI_HOST)"

# ── Step 2: Transfer project files ────────────────────────────────────────────
if [ "$SKIP_TRANSFER" = false ]; then
    echo ""
    echo "[2] Transferring project files to Pi..."

    # Ensure remote directories exist
    $SSH "mkdir -p $PI_DIR/samples $PI_DIR/results $PI_DIR/samples/keys2"

    # Transfer source code directories (not venv, not samples/keys/)
    for dir in encryption watermark verification provenance utils raspberry_pi scripts docs; do
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            echo "  -> $dir/"
            $SCP -r "$PROJECT_ROOT/$dir" "$PI_USER@$PI_HOST:$PI_DIR/"
        fi
    done

    # Transfer root-level Python files
    for f in main.py transfer.py gui_verify.py web_verify.py requirements.txt ADDITIONS.md README.md; do
        if [ -f "$PROJECT_ROOT/$f" ]; then
            echo "  -> $f"
            $SCP "$PROJECT_ROOT/$f" "$PI_USER@$PI_HOST:$PI_DIR/"
        fi
    done

    # Transfer generated sample files (never transfer private.pem)
    echo ""
    echo "  Transferring sample files (no private keys)..."
    SAMPLE_FILES=(
        "samples/input.png"
        "samples/input1.png"
        "samples/watermarked.png"
        "samples/watermarked2.png"
        "samples/watermarked_v2.png"
        "samples/watermarked_v3.png"
        "samples/watermarked2_v2.png"
        "samples/watermarked2_v3.png"
        "samples/manifest.json"
        "samples/manifest2.json"
        "samples/manifest_v2.json"
        "samples/manifest_v3.json"
        "samples/manifest2_v2.json"
        "samples/manifest2_v3.json"
        "samples/registry.json"
        "samples/registry2.json"
        "samples/provenance.json"
        "samples/provenance2.json"
    )
    for f in "${SAMPLE_FILES[@]}"; do
        if [ -f "$PROJECT_ROOT/$f" ]; then
            echo "  -> $f"
            $SCP "$PROJECT_ROOT/$f" "$PI_USER@$PI_HOST:$PI_DIR/$f"
        else
            echo "  (skip, not found) $f"
        fi
    done

    echo "  File transfer complete ✓"
fi

# ── Step 3: Remote setup (venv + deps + GPIO) ─────────────────────────────────
if [ "$SKIP_SETUP" = false ]; then
    echo ""
    echo "[3] Setting up Python environment on Pi..."

    $SSH bash << 'REMOTE_SETUP'
set -euo pipefail
cd ~/SecureDocSystem

echo "  Creating venv..."
python3 -m venv --system-site-packages venv
source venv/bin/activate

echo "  Installing Python requirements..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "  Installing psutil for benchmark..."
pip install --quiet psutil

echo "  Detecting Pi model and installing GPIO library..."
bash raspberry_pi/install_gpio.sh

echo ""
echo "  Python environment ready ✓"
python3 -c "
import cv2, numpy, Crypto
print('  opencv       :', cv2.__version__)
print('  numpy        :', numpy.__version__)
print('  pycryptodome : OK')
try:
    import RPi.GPIO as G
    print('  GPIO         : RPi.GPIO', G.VERSION)
except ImportError:
    try:
        import lgpio
        print('  GPIO         : lgpio (rpi-lgpio)')
    except ImportError:
        print('  GPIO         : not found (check install_gpio.sh)')
"
REMOTE_SETUP

fi

# ── Step 4: Quick smoke test on Pi ────────────────────────────────────────────
echo ""
echo "[4] Running smoke-test verification on Pi..."

$SSH bash << 'REMOTE_VERIFY'
set -euo pipefail
cd ~/SecureDocSystem
source venv/bin/activate
export PYTHONIOENCODING=utf-8

echo ""
echo "  --- Pi model ---"
cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "  (non-Pi or no model file)"
echo ""

echo "  --- Verifying DOC-2026-001 (input.png) ---"
python3 raspberry_pi/pi_verify_terminal.py \
    --file     samples/watermarked.png \
    --manifest samples/manifest.json \
    --registry samples/registry.json \
    --provenance samples/provenance.json \
    --mode online --no-led

echo ""
echo "  --- Verifying DOC-2026-002 (input1.jpg) ---"
python3 raspberry_pi/pi_verify_terminal.py \
    --file     samples/watermarked2.png \
    --manifest samples/manifest2.json \
    --registry samples/registry2.json \
    --provenance samples/provenance2.json \
    --mode online --no-led
REMOTE_VERIFY

echo ""
echo "========================================================"
echo "  Deployment complete ✓"
echo ""
echo "  To run the full demo on the Pi:"
echo "    ssh $PI_USER@$PI_HOST"
echo "    cd SecureDocSystem && source venv/bin/activate"
echo "    python3 scripts/pi_demo.py --skip-issue"
echo ""
echo "  For LED test (hardware wired):"
echo "    python3 raspberry_pi/led_test.py"
echo ""
echo "  For benchmark:"
echo "    python3 raspberry_pi/benchmark.py \\"
echo "        --file samples/watermarked.png \\"
echo "        --manifest samples/manifest.json \\"
echo "        --provenance samples/provenance.json -n 30"
echo "========================================================"
