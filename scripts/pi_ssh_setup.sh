#!/usr/bin/env bash
# =============================================================================
# scripts/pi_ssh_setup.sh
# Run this ONCE inside a terminal on the Raspberry Pi (via VNC or local keyboard).
#
# What it does:
#   1. Enables and starts the SSH service
#   2. Adds the 'fun' user to the gpio group (no sudo needed for GPIO later)
#   3. Installs system packages needed by the project
#   4. Creates the project directory and virtual environment
#   5. Prints the Pi's IP so you can confirm it matches 10.1.14.11
#
# How to run (in the VNC terminal on the Pi):
#   bash ~/pi_ssh_setup.sh
#
# After this script completes, SSH will be available from your laptop at:
#   ssh fun@10.1.14.11
# =============================================================================

set -euo pipefail

PI_USER="${USER:-fun}"
PROJECT_DIR="${HOME}/SecureDocSystem"

echo "========================================"
echo "  Pi SSH + Project Setup"
echo "  User: $PI_USER"
echo "========================================"

# ── Step 1: Enable SSH ────────────────────────────────────────────────────────
echo ""
echo "[1/5] Enabling SSH service..."
sudo systemctl enable ssh
sudo systemctl start ssh
SSH_STATUS=$(sudo systemctl is-active ssh 2>/dev/null || echo "unknown")
echo "  SSH status: $SSH_STATUS"
if [ "$SSH_STATUS" != "active" ]; then
    echo "  Trying raspi-config method..."
    sudo raspi-config nonint do_ssh 0   # 0 = enable
fi

# Confirm SSH is listening
sleep 1
if ss -tlnp 2>/dev/null | grep -q ':22'; then
    echo "  SSH is listening on port 22 ✓"
else
    echo "  WARNING: port 22 not detected — check 'sudo systemctl status ssh'"
fi

# ── Step 2: GPIO group ────────────────────────────────────────────────────────
echo ""
echo "[2/5] Adding $PI_USER to gpio group..."
if groups "$PI_USER" | grep -q gpio; then
    echo "  Already in gpio group ✓"
else
    sudo usermod -aG gpio "$PI_USER"
    echo "  Added to gpio group (re-login needed for effect)"
fi

# ── Step 3: System packages ───────────────────────────────────────────────────
echo ""
echo "[3/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    python3-pip \
    python3-venv \
    python3-opencv \
    python3-numpy \
    libatlas-base-dev \
    libopenjp2-7 \
    libtiff-dev \
    git
echo "  System packages installed ✓"

# ── Step 4: Create project directory ─────────────────────────────────────────
echo ""
echo "[4/5] Creating project directory..."
mkdir -p "$PROJECT_DIR/samples"
mkdir -p "$PROJECT_DIR/results"
echo "  $PROJECT_DIR created ✓"

# ── Step 5: Print network info ────────────────────────────────────────────────
echo ""
echo "[5/5] Network information:"
hostname -I | tr ' ' '\n' | grep -v '^$' | while read -r ip; do
    echo "  IP: $ip"
done
echo "  Hostname: $(hostname)"

echo ""
echo "========================================"
echo "  Setup complete!"
echo ""
echo "  From your laptop, you can now:"
echo "  ssh $PI_USER@$(hostname -I | awk '{print $1}')"
echo ""
echo "  Then run the deployment:"
echo "  bash scripts/pi_deploy.sh"
echo "========================================"
