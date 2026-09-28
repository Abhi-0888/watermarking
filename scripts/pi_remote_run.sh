#!/usr/bin/env bash
# =============================================================================
# scripts/pi_remote_run.sh
# SSH into the Pi and run the complete demo + verification remotely.
#
# Usage (from project root on your laptop, after pi_deploy.sh has run):
#
#   bash scripts/pi_remote_run.sh                    # full demo (skip issuance)
#   bash scripts/pi_remote_run.sh --full             # include issuance + transfers
#   bash scripts/pi_remote_run.sh --led              # enable GPIO LED output
#   bash scripts/pi_remote_run.sh --input1           # run on input1 (DOC-2026-002)
#   bash scripts/pi_remote_run.sh --benchmark        # run 30-pass benchmark only
#   bash scripts/pi_remote_run.sh --led-test         # run LED wiring test only
#   bash scripts/pi_remote_run.sh --tamper-only      # stages 5 only
# =============================================================================

set -euo pipefail

PI_HOST="10.1.14.11"
PI_USER="fun"
PI_PORT="22"
PI_DIR="~/SecureDocSystem"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
SSH="ssh -p $PI_PORT $SSH_OPTS $PI_USER@$PI_HOST"

# ── Parse flags ───────────────────────────────────────────────────────────────
FULL=false
LED=false
INPUT1=false
BENCHMARK=false
LED_TEST=false
TAMPER_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --full)        FULL=true ;;
        --led)         LED=true ;;
        --input1)      INPUT1=true ;;
        --benchmark)   BENCHMARK=true ;;
        --led-test)    LED_TEST=true ;;
        --tamper-only) TAMPER_ONLY=true ;;
    esac
done

LED_FLAG="--no-led"
if [ "$LED" = true ]; then LED_FLAG=""; fi

SKIP_ISSUE_FLAG="--skip-issue"
if [ "$FULL" = true ]; then SKIP_ISSUE_FLAG=""; fi

echo "========================================================"
echo "  Pi Remote Run — $PI_USER@$PI_HOST"
echo "  LED output : $LED"
echo "  Full run   : $FULL"
echo "  Input1     : $INPUT1"
echo "========================================================"

# ── Check SSH ─────────────────────────────────────────────────────────────────
if ! $SSH "echo SSH_OK" 2>/dev/null | grep -q "SSH_OK"; then
    echo "ERROR: SSH not available. Run pi_deploy.sh first."
    exit 1
fi
echo "SSH connected ✓"

# ── LED wiring test ───────────────────────────────────────────────────────────
if [ "$LED_TEST" = true ]; then
    echo ""
    echo "--- Running LED wiring test ---"
    $SSH "cd $PI_DIR && source venv/bin/activate && export PYTHONIOENCODING=utf-8 && python3 raspberry_pi/led_test.py"
    exit 0
fi

# ── Benchmark only ────────────────────────────────────────────────────────────
if [ "$BENCHMARK" = true ]; then
    echo ""
    echo "--- Running 30-pass benchmark on DOC-2026-001 ---"
    $SSH "cd $PI_DIR && source venv/bin/activate && export PYTHONIOENCODING=utf-8 && \
        python3 raspberry_pi/benchmark.py \
            --file samples/watermarked.png \
            --manifest samples/manifest.json \
            --provenance samples/provenance.json \
            --mode online -n 30"

    echo ""
    echo "--- Benchmark CSV ---"
    $SSH "cat $PI_DIR/results/pi_benchmark.csv"
    exit 0
fi

# ── Main demo ─────────────────────────────────────────────────────────────────
if [ "$INPUT1" = false ]; then
    echo ""
    echo "--- Running pi_demo.py on DOC-2026-001 (input.png) ---"
    $SSH "cd $PI_DIR && source venv/bin/activate && export PYTHONIOENCODING=utf-8 && \
        python3 scripts/pi_demo.py $LED_FLAG $SKIP_ISSUE_FLAG --mode online"
else
    echo ""
    echo "--- Running run_input1.py on DOC-2026-002 (input1.jpg) ---"
    $SSH "cd $PI_DIR && source venv/bin/activate && export PYTHONIOENCODING=utf-8 && \
        python3 scripts/run_input1.py $LED_FLAG $SKIP_ISSUE_FLAG --mode online"
fi

echo ""
echo "========================================================"
echo "  Remote run complete."
echo ""
echo "  To open an interactive shell on the Pi:"
echo "    ssh $PI_USER@$PI_HOST"
echo "========================================================"
