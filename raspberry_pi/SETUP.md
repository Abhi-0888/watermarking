# Raspberry Pi Setup — SecureDocSystem

## Hardware requirements

| Component | Notes |
|-----------|-------|
| Raspberry Pi 3B+ / 4B / 5 (or Zero 2 W) | Pi 5 needs `rpi-lgpio` instead of `RPi.GPIO` |
| MicroSD (≥ 16 GB, class 10) | Raspberry Pi OS (Bookworm or Bullseye) |
| Green LED + 330 Ω resistor | GPIO17 → LED+ → resistor → GND |
| Red LED + 330 Ω resistor | GPIO27 → LED+ → resistor → GND |
| HDMI monitor (optional) | Dashboard / fullscreen kiosk |
| USB keyboard / mouse | First-time config only |

### Wiring diagram (BCM numbering)

```
Pin 11 (GPIO17)  ---[330Ω]--- GREEN LED anode --- GND (Pin 9)
Pin 13 (GPIO27)  ---[330Ω]--- RED   LED anode --- GND (Pin 14)
```

Optional buzzer (Step 7):
```
Pin 16 (GPIO23)  ---[100Ω]--- Buzzer + --- GND (Pin 14)
```

---

## 1. First-time OS preparation

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-opencv \
                    libatlas-base-dev libopenjp2-7 libtiff-dev \
                    python3-numpy git
```

---

## 2. Clone / copy the project

```bash
# From the desktop/laptop (adjust paths and Pi IP):
scp -r SecureDocSystem pi@<pi-ip>:~/SecureDocSystem
# DO NOT copy samples/keys/private.pem — verification needs only the public key
# embedded in manifest.json.
```

---

## 3. Create virtual environment

```bash
cd ~/SecureDocSystem

# --system-site-packages lets opencv-python (installed system-wide) be
# visible inside the venv without a slow pip re-compile.
python3 -m venv --system-site-packages venv
source venv/bin/activate
```

---

## 4. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt

# Auto-detects Pi model and installs the right GPIO library:
bash raspberry_pi/install_gpio.sh

# For benchmark.py (included in requirements-pi.txt):
pip install psutil
```

### What `install_gpio.sh` does

| Pi model | Package installed |
|----------|-------------------|
| Pi 5     | `rpi-lgpio` (lgpio back-end) |
| Pi 3/4/Zero | `RPi.GPIO` |
| Non-Pi   | nothing (mock mode used automatically) |

---

## 5. GPIO group permission (no sudo for main app)

```bash
sudo usermod -aG gpio $USER
# Log out and back in (or reboot) for the group to take effect.
# Verify:
groups | grep gpio
```

---

## 6. Confirm imports

```bash
python3 - <<'EOF'
import cv2, numpy, Crypto
print("opencv       :", cv2.__version__)
print("numpy        :", numpy.__version__)
print("pycryptodome : OK")
try:
    import RPi.GPIO as GPIO
    print("GPIO         : RPi.GPIO", GPIO.VERSION)
except ImportError:
    try:
        import lgpio
        print("GPIO         : lgpio (rpi-lgpio back-end)")
    except ImportError:
        print("GPIO         : not available (mock mode)")
EOF
```

---

## 7. One-command end-to-end demo (NEW — recommended)

This single command runs the **complete pipeline**:
issue document → 2 transfers → verify authentic copy → test all 4 tamper variants.

```bash
# Plain-print mode (works over SSH, no display needed):
bash scripts/pi_demo.sh

# Or directly with Python:
python3 scripts/pi_demo.py

# With HDMI curses fullscreen display:
python3 scripts/pi_demo.py --fullscreen

# Skip LED (bench testing without wired LEDs):
python3 scripts/pi_demo.py --no-led

# Skip issuance if samples already generated (faster re-run):
python3 scripts/pi_demo.py --no-led --skip-issue
```

What it does:

| Stage | Action | Expected result |
|-------|--------|-----------------|
| 1 | `main.py demo` — issue document | `watermarked.png`, `manifest.json`, `registry.json`, `provenance.json` created |
| 2 | Transfer Abhishek → Rahul | `watermarked_v2.png` + updated chain |
| 3 | Transfer Rahul → Priya | `watermarked_v3.png` + updated chain |
| 4 | Pi terminal — authentic copy | **AUTHENTIC** · GREEN LED · traversal path printed |
| 5a | Tamper: painted patch | **TAMPERED** · RED LED · block labels e.g. B16-17…B18-20 |
| 5b | Tamper: text overlay | **TAMPERED** · RED LED · ~46 flagged blocks |
| 5c | Redistribution: JPEG Q=50 | **TAMPERED** (watermark destroyed at Q=50) |
| 5d | Redistribution: 32px crop | **TAMPERED** (hash + sig fail; geometry mismatch) |

Exit code 0 if the authentic copy verifies correctly; non-zero otherwise.

---

## 8. Manual step-by-step (alternative to one-command demo)

Use this if you want to see each phase individually.

```bash
# Step A — Issue document
python3 main.py demo

# Step B — Transfers
python3 transfer.py --doc-id DOC-2026-001 --from Abhishek --to Rahul
python3 transfer.py --doc-id DOC-2026-001 --from Rahul --to Priya

# Step C — Verify (all paths are now DEFAULT — no flags required)
python3 raspberry_pi/pi_verify_terminal.py

# Or with explicit paths (identical result):
python3 raspberry_pi/pi_verify_terminal.py \
    --file     samples/watermarked.png \
    --manifest samples/manifest.json \
    --registry samples/registry.json \
    --provenance samples/provenance.json \
    --mode online

# Step D — Verify + auto-issue in one command
python3 raspberry_pi/pi_verify_terminal.py --demo
```

Expected output excerpt:
```
Traversal Path    : CollegeXYZ -> Abhishek -> Rahul -> Priya
Verdict           : AUTHENTIC
```

---

## 9. Test LEDs (wiring check)

```bash
python3 raspberry_pi/led_test.py
# Cycles: GREEN on (1 s) → RED on (1 s) → BOTH blink 3× → all off
# Safe to run on a laptop too — falls back to [mock LED] on non-Pi hardware.
```

Confirm real hardware is detected:
```bash
python3 -c "from raspberry_pi.gpio_led import HARDWARE_AVAILABLE; print('Hardware GPIO:', HARDWARE_AVAILABLE)"
```

---

## 10. Fullscreen display (VNC / HDMI)

```bash
# Resize VNC terminal to at least 55 × 22 characters first, then:
python3 raspberry_pi/pi_verify_terminal.py --fullscreen
# (uses default sample paths — no extra flags needed)
# Press any key or wait 8 s for the dashboard to close.
```

The dashboard shows:
- Title row highlighted with reverse video
- STATUS in **green** (AUTHENTIC) or **red** (TAMPERED)
- Traversal path in cyan
- "Press any key to dismiss" footer

Falls back to plain-print automatically if the terminal is too small or
curses is unavailable (e.g. piped output).

---

## 11. Benchmark

```bash
python3 raspberry_pi/benchmark.py \
    --file     samples/watermarked.png \
    --manifest samples/manifest.json \
    --provenance samples/provenance.json \
    -n 30
# Prints mean/median/min/max for time, memory, CPU.
# Saves results to results/pi_benchmark.csv with Pi model in header.
```

---

## 12. Optional buzzer

Wire an active or passive buzzer to **GPIO23** (Pin 16), then edit one line in
`raspberry_pi/gpio_led.py`:

```python
BUZZER_PIN = 23   # was None
```

Behaviour after the change:
- `set_status(authentic=False)` → double-beep on tamper
- `blink_error()` → triple-beep on hard failure

No other code changes needed. All buzzer output is guarded by `HARDWARE_AVAILABLE`
and `buzzer_pin is not None`, so the rest of the system is unaffected.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `RuntimeError: No access to /dev/mem` | Add user to `gpio` group (step 5) and reboot |
| `ModuleNotFoundError: RPi` on Pi 5 | Run `bash raspberry_pi/install_gpio.sh` again |
| `cv2` import error inside venv | Re-create venv with `--system-site-packages` |
| Curses blank / garbled in VNC | Resize terminal to ≥55 cols × 22 rows before `--fullscreen` |
| `[mock LED]` on real Pi | GPIO library missing; check `python3 -c "import RPi.GPIO"` |
| `samples/watermarked.png not found` | Run `python3 main.py demo` (or `--demo` flag) first |
| Box-drawing characters look wrong | Set `export PYTHONIOENCODING=utf-8` before running |
