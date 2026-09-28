#!/usr/bin/env bash
# install_gpio.sh — install the right GPIO library for this Pi model.
# Run inside the activated venv:
#   source venv/bin/activate
#   bash raspberry_pi/install_gpio.sh
#
# Pi 5  → rpi-lgpio  (uses the kernel lgpio back-end; RPi.GPIO not supported)
# Pi 3/4 / Zero → RPi.GPIO
# Non-Pi → prints a message and exits cleanly (mock mode will be used)

set -euo pipefail

MODEL_FILE="/proc/device-tree/model"

if [ ! -f "$MODEL_FILE" ]; then
    echo "[install_gpio] Not running on a Raspberry Pi — GPIO mock mode will be used."
    exit 0
fi

MODEL=$(cat "$MODEL_FILE" | tr -d '\0')
echo "[install_gpio] Detected model: $MODEL"

if echo "$MODEL" | grep -qi "Raspberry Pi 5"; then
    echo "[install_gpio] Pi 5 detected → installing rpi-lgpio"
    pip install --quiet rpi-lgpio
    echo "[install_gpio] rpi-lgpio installed successfully."
else
    echo "[install_gpio] Pi 3/4/Zero detected → installing RPi.GPIO"
    pip install --quiet RPi.GPIO
    echo "[install_gpio] RPi.GPIO installed successfully."
fi
