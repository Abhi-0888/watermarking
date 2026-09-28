# Deployment Guide — Real Raspberry Pi at 10.1.14.11

This document is the single source of truth for deploying and running
SecureDocSystem on the physical Raspberry Pi that is already on the network.

```
Pi IP       : 10.1.14.11
Pi username : fun
VNC port    : 5900  (RealVNC — currently OPEN)
SSH port    : 22    (must be enabled once via VNC — see Step 1)
```

---

## Prerequisites (laptop side)

| Requirement | How to check |
|-------------|-------------|
| OpenSSH client | `ssh -V` in PowerShell / Git Bash |
| `scp` available | `scp` — ships with OpenSSH on Windows 10/11 |
| Sample files generated | `samples/watermarked.png` must exist — run `py -3 scripts/pi_demo.py --no-led` first |
| Git Bash or WSL | For running `.sh` scripts on Windows |

> **Windows note:** All `.sh` scripts must be run inside **Git Bash** or **WSL**, not PowerShell.
> Alternatively, each command can be typed manually — every step is spelled out below.

---

## Step 1 — Enable SSH on the Pi (one-time, via VNC)

SSH is currently **disabled** on the Pi. You need to enable it once using RealVNC.

### 1a. Connect with RealVNC Viewer

1. Open **RealVNC Viewer** on your laptop.
2. Enter address: `10.1.14.11`
3. When prompted for authentication:
   - Click **"I have a catchphrase"**
   - Catchphrase: `Audio neon fossil. Ticket Gong Ringo.`
   - Signature shown should match: `5d-73-2e-ae-7e-cd-fe-62`
4. Click **Connect**.

### 1b. Open a terminal on the Pi desktop

On the Pi's VNC desktop, open a terminal (right-click desktop → Terminal, or use
the taskbar launcher).

### 1c. Enable SSH (type these commands in the Pi terminal)

```bash
sudo systemctl enable ssh
sudo systemctl start ssh
sudo systemctl status ssh   # should show: active (running)
```

Verify it's listening:
```bash
ss -tlnp | grep :22
# Expected: LISTEN on 0.0.0.0:22
```

### 1d. Add 'fun' to gpio group (no sudo for LED/GPIO)

```bash
sudo usermod -aG gpio fun
```
> Log out and back in (or reboot) for the group change to take effect.

### 1e. Install system packages

```bash
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv python3-opencv \
    libatlas-base-dev libopenjp2-7 libtiff-dev python3-numpy
```

### 1f. Confirm Pi's IP

```bash
hostname -I
# Should include: 10.1.14.11
```

---

## Step 2 — Deploy from laptop (SSH must be working)

All commands below run on your **laptop** in Git Bash or WSL from the project root.

### 2a. Test SSH access first

```bash
ssh -o StrictHostKeyChecking=accept-new fun@10.1.14.11
# Expected: welcome message, Pi prompt
exit
```

If SSH works, proceed. If not, go back to Step 1.

### 2b. Run the deployment script

```bash
bash scripts/pi_deploy.sh
```

This does everything in one command:
1. Verifies SSH is reachable
2. Transfers all project source files to `/home/fun/SecureDocSystem/`
3. Transfers all generated sample files (manifest, watermarked image, provenance chain)  
   **Private key (`samples/keys/private.pem`) is never transferred**
4. Creates a Python venv with `--system-site-packages` on the Pi
5. Installs `requirements.txt` + `psutil`
6. Runs `install_gpio.sh` (auto-picks `rpi-lgpio` for Pi 5 or `RPi.GPIO` for Pi 3/4)
7. Runs a smoke-test verification of both documents on the Pi

Expected final output:
```
SSH connected ✓
File transfer complete ✓
Python environment ready ✓
  opencv       : 4.x.x
  numpy        : 1.x.x
  pycryptodome : OK
  GPIO         : RPi.GPIO 0.7.x  (or lgpio for Pi 5)
...
Traversal Path    : CollegeXYZ -> Abhishek -> Rahul -> Priya
Verdict           : AUTHENTIC
...
Deployment complete ✓
```

---

## Step 3 — Run the full demo remotely

After deployment, run everything from your laptop via SSH:

```bash
# Full demo on input.png (DOC-2026-001), skip issuance (already done):
bash scripts/pi_remote_run.sh

# Full demo on input1.jpg (DOC-2026-002):
bash scripts/pi_remote_run.sh --input1

# Enable real GPIO LEDs:
bash scripts/pi_remote_run.sh --led

# LED wiring test (green → red → both → off):
bash scripts/pi_remote_run.sh --led-test

# 30-pass performance benchmark:
bash scripts/pi_remote_run.sh --benchmark

# Re-issue documents then run everything (slow, ~2 min):
bash scripts/pi_remote_run.sh --full
```

---

## Step 4 — Interactive session on the Pi

```bash
ssh fun@10.1.14.11
cd SecureDocSystem
source venv/bin/activate
export PYTHONIOENCODING=utf-8

# Verify (defaults point to samples/ automatically — no flags needed):
python3 raspberry_pi/pi_verify_terminal.py

# Verify with fullscreen curses dashboard (in VNC terminal):
python3 raspberry_pi/pi_verify_terminal.py --fullscreen

# Full end-to-end demo (files already on Pi):
python3 scripts/pi_demo.py --skip-issue

# Full demo on input1:
python3 scripts/run_input1.py --skip-issue

# LED wiring test:
python3 raspberry_pi/led_test.py

# Benchmark:
python3 raspberry_pi/benchmark.py \
    --file samples/watermarked.png \
    --manifest samples/manifest.json \
    --provenance samples/provenance.json \
    -n 30
```

---

## Step 5 — Manual verification commands (explicit paths)

```bash
# DOC-2026-001 (input.png)
python3 raspberry_pi/pi_verify_terminal.py \
    --file     samples/watermarked.png \
    --manifest samples/manifest.json \
    --registry samples/registry.json \
    --provenance samples/provenance.json \
    --mode online

# DOC-2026-002 (input1.jpg)
python3 raspberry_pi/pi_verify_terminal.py \
    --file     samples/watermarked2.png \
    --manifest samples/manifest2.json \
    --registry samples/registry2.json \
    --provenance samples/provenance2.json \
    --mode online
```

---

## Step 6 — Tamper tests on Pi hardware

```bash
# Create tampered variants on the Pi:
python3 scripts/make_tampered.py

# Verify each (LEDs will respond if wired):
for VARIANT in tampered_patch tampered_text tampered_jpeg tampered_crop; do
  echo "=== $VARIANT ==="
  python3 raspberry_pi/pi_verify_terminal.py \
      --file samples/tampered/${VARIANT}.png \
      --manifest samples/manifest.json \
      --registry samples/registry.json \
      --provenance samples/provenance.json \
      --mode online
done
```

---

## Wiring reminder

```
Pin 11 (GPIO17)  ---[330Ω]--- GREEN LED anode ---+--- GND (Pin 9)
Pin 13 (GPIO27)  ---[330Ω]--- RED   LED anode ---+--- GND (Pin 14)
Pin 16 (GPIO23)  ---[100Ω]--- Buzzer  +      ---+--- GND (Pin 14)  [optional]
```

Enable buzzer: set `BUZZER_PIN = 23` in `raspberry_pi/gpio_led.py`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ssh: connect to host 10.1.14.11 port 22: Connection refused` | Step 1 not done — enable SSH via VNC |
| `ssh: connect to host 10.1.14.11 port 22: No route to host` | Pi and laptop on different subnets — check Wi-Fi/Ethernet |
| `Permission denied (publickey)` | Use password auth: add `-o PubkeyAuthentication=no` to ssh opts, or copy your SSH key: `ssh-copy-id fun@10.1.14.11` |
| `cv2` import error inside venv | Recreate venv with `python3 -m venv --system-site-packages venv` |
| `ModuleNotFoundError: RPi` on Pi 5 | Run `bash raspberry_pi/install_gpio.sh` again |
| `RuntimeError: No access to /dev/mem` | `sudo usermod -aG gpio fun` then reboot |
| `[mock LED]` instead of real LED | GPIO library missing or not in gpio group |
| Box chars garbled in SSH terminal | `export PYTHONIOENCODING=utf-8` before running |
| Watermark score 0.0 on Pi | Wrong file/manifest pair — check `--file` and `--manifest` match |
| `Watermarked file not found` | Run `py -3 scripts/pi_demo.py --no-led` on laptop first, then re-deploy |

---

## File layout on the Pi after deployment

```
/home/fun/SecureDocSystem/
├── main.py
├── transfer.py
├── requirements.txt
├── raspberry_pi/
│   ├── pi_verify_terminal.py   ← primary verification script
│   ├── gpio_led.py             ← LED + buzzer driver
│   ├── monitor_display.py      ← dashboard (plain + curses)
│   ├── benchmark.py
│   ├── led_test.py
│   ├── pi_deploy_config.py     ← IP / paths config
│   └── install_gpio.sh
├── scripts/
│   ├── pi_demo.py              ← full 5-stage demo
│   ├── run_input1.py           ← input1.jpg demo
│   └── make_tampered.py
├── samples/
│   ├── input.png               ← source image 1
│   ├── input1.png              ← source image 2 (hand photo)
│   ├── watermarked.png         ← DOC-2026-001 current copy
│   ├── watermarked2.png        ← DOC-2026-002 current copy
│   ├── manifest.json           ← DOC-2026-001 manifest
│   ├── manifest2.json          ← DOC-2026-002 manifest
│   ├── registry.json           ← DOC-2026-001 registry
│   ├── registry2.json          ← DOC-2026-002 registry
│   ├── provenance.json         ← DOC-2026-001 chain
│   └── provenance2.json        ← DOC-2026-002 chain
│   NOTE: keys/ is NOT transferred (private key stays on laptop only)
├── results/                    ← benchmark CSV written here
└── venv/                       ← Python venv (created on Pi)
```

---

## Security notes

- `samples/keys/private.pem` is **never** transferred to the Pi.
  The Pi holds only the **public key** (embedded in each manifest JSON).
- Verification (`verify_document`) uses only the public key — no signing on Pi.
- The Pi is a read-only verification terminal: it cannot issue or re-sign documents.
- VNC catchphrase is used only for the one-time SSH-enable step; subsequent
  access is via SSH key or password.
