# Secure Digital Document Protection System

A Python system that protects digital documents using hybrid encryption, invisible watermarking, tamper detection, provenance tracking, and forensic traceability — with desktop, web, and Raspberry Pi verification interfaces.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/LITERATURE_REVIEW.md](docs/LITERATURE_REVIEW.md) | Related work comparison and research gap |
| [docs/PRESENTATION.md](docs/PRESENTATION.md) | Slide-by-slide presentation and demo script |

## Features

- **Hybrid cryptography** — AES file encryption, RSA key protection, SHA-256 hashing, digital signatures
- **Invisible watermarking** — DCT-domain embedding with issuer, sender, receiver, document ID, version, and timestamp
- **Verification** — Offline (manifest) and online (registry) modes
- **Tamper localization** — Block-level (16×16) fingerprinting to pinpoint edited regions
- **Provenance chain** — Hash-linked transfer history (e.g. College → Abhishek → Rahul → Priya)
- **Authorized transfers** — Re-watermark, re-sign, and append provenance on each handoff
- **Leak traceability** — Recover recipient identity from a leaked copy
- **Attack evaluation** — Compression, cropping, scaling, screenshot, and minor-edit simulation
- **Raspberry Pi terminal** — HDMI dashboard + green/red LED status (mock mode on non-Pi hardware)

## Project Structure

```
SecureDocSystem/
├── main.py                 # Issue, demo, full evaluation, verify CLI
├── transfer.py             # Authorized document transfer CLI
├── gui_verify.py           # Desktop upload verifier
├── web_verify.py           # Browser-based verifier
├── requirements.txt
├── docs/
│   ├── LITERATURE_REVIEW.md  # Related work and research gap
│   └── PRESENTATION.md       # Slide-by-slide presentation guide
├── encryption/
│   ├── aes.py              # AES encrypt/decrypt
│   └── rsa.py              # RSA key generation, key wrap, save/load
├── watermark/
│   ├── embed.py            # DCT watermark embedding
│   └── extract.py          # Watermark extraction
├── verification/
│   ├── verify.py           # Full verification pipeline
│   ├── package.py          # Manifest and registry
│   ├── attacks.py            # Attack simulation
│   └── tamper_localization.py
├── provenance/
│   └── chain.py            # Hash-linked traversal registry
├── utils/
│   ├── hash.py             # SHA-256, signing helpers
│   ├── forensics.py        # Leak traceability reports
│   └── metrics.py          # PSNR, accuracy, timing
├── raspberry_pi/
│   ├── pi_verify_terminal.py
│   ├── gpio_led.py
│   ├── monitor_display.py
│   └── requirements-pi.txt   # Pi-only: RPi.GPIO
└── samples/
    ├── input.png           # Source document (required)
    ├── keys/               # Issuer keypair (created on first run)
    └── attacks/            # Attack outputs (created by full evaluation)
```

Generated at runtime (not committed): `encrypted.bin`, `decrypted.png`, `watermarked.png`, `manifest.json`, `registry.json`, `provenance.json`.

## Requirements

```bash
pip install -r requirements.txt
```

| Package        | Purpose              |
|----------------|----------------------|
| numpy          | Numerical operations |
| opencv-python  | Image I/O, DCT       |
| pycryptodome   | AES, RSA, signatures |
| pywavelets     | Wavelet transforms   |
| flask          | Web verifier         |
| requests       | HTTP helpers         |

On Raspberry Pi, also install: `pip install -r raspberry_pi/requirements-pi.txt`

## Quick Start

```bash
# Issue a protected document (v1: College → Abhishek)
py -3 main.py demo

# Transfer to new holders
py -3 transfer.py --doc-id DOC-2026-001 --from Abhishek --to Rahul
py -3 transfer.py --doc-id DOC-2026-001 --from Rahul --to Priya

# Verify with full provenance
py -3 main.py verify --file samples/watermarked.png --manifest samples/manifest.json \
    --mode online --registry samples/registry.json --provenance samples/provenance.json
```

## Commands

| Command | Description |
|---------|-------------|
| `py -3 main.py present` | Fast live demo (~5 s) |
| `py -3 main.py demo` | Quick demo with verification |
| `py -3 main.py full` | Full evaluation + attack simulation (~40 s) |
| `py -3 main.py verify --file … --manifest …` | Verify an existing protected file |
| `py -3 transfer.py --doc-id … --from … --to …` | Authorized transfer |
| `py -3 gui_verify.py` | Desktop upload verifier |
| `py -3 web_verify.py` | Web upload verifier |
| `py -3 raspberry_pi/pi_verify_terminal.py …` | Pi verification terminal |

Verify flags: `--mode offline|online`, `--registry`, `--provenance`

## Pipeline

1. Encrypt original document with AES; protect AES key with RSA
2. Embed invisible personalized watermark into the delivered copy
3. Hash and digitally sign the protected file
4. Write manifest (offline verification) and registry entry (online verification)
5. Initialize provenance chain and tamper-localization baseline
6. On transfer: re-embed watermark, re-sign, re-baseline, append provenance record
7. On verify: check hash, signature, watermark, registry, tamper blocks, provenance chain

## Watermark Format

```
ISS:<issuer>|SRC:<sender>|RCV:<receiver>|DOC:<document_id>|VER:<version>|TS:<timestamp>
```

Example:

```
ISS:CollegeXYZ|SRC:CollegeXYZ|RCV:Abhishek|DOC:DOC-2026-001|VER:1|TS:2026-09-15 14:51:42
```

| Field | Meaning |
|-------|---------|
| ISS   | Original issuer |
| SRC   | Current sender handing off this copy |
| RCV   | Receiver of this copy |
| DOC   | Document ID |
| VER   | Copy version (increments on each transfer) |
| TS    | Timestamp |

Embedding capacity: **128 characters**.

## Verification Checks

| Check | Offline | Online |
|-------|---------|--------|
| SHA-256 hash | ✓ | ✓ |
| Digital signature | ✓ | ✓ |
| Watermark match | ✓ | ✓ |
| Registry lookup | — | ✓ |
| Tamper localization | ✓ | ✓ |
| Provenance chain | ✓ (if file provided) | ✓ |

## Raspberry Pi Terminal

The Pi is a **verification terminal** — it never holds the issuer private key (only the public key embedded in the manifest).

### Hardware

- Raspberry Pi 3B+/4/5 (Pi Zero 2 W works, slower)
- Green LED → GPIO17 (pin 11), Red LED → GPIO27 (pin 13)
- 330 Ω resistors, breadboard, jumper wires
- Optional HDMI monitor for dashboard

Update `GREEN_PIN` / `RED_PIN` in `raspberry_pi/gpio_led.py` if your wiring differs.

### Install (on Pi)

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv libatlas-base-dev
cd SecureDocSystem
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r raspberry_pi/requirements-pi.txt
```

Copy verification files to the Pi (not `samples/keys/private.pem`):

```bash
scp samples/watermarked.png samples/manifest.json samples/registry.json \
    samples/provenance.json pi@<pi-ip>:~/SecureDocSystem/samples/
```

### Run

```bash
python3 raspberry_pi/pi_verify_terminal.py \
  --file samples/watermarked.png \
  --manifest samples/manifest.json \
  --registry samples/registry.json \
  --provenance samples/provenance.json \
  --mode online
```

Add `--fullscreen` for HDMI curses dashboard, or `--watch /path/to/folder` for kiosk mode.

On non-Pi machines, LEDs auto-fallback to `[mock LED] GREEN/RED` console output.

### Boot service (optional)

Create `/etc/systemd/system/doc-verify.service`:

```ini
[Unit]
Description=Secure Document Verification Terminal
After=multi-user.target

[Service]
Type=simple
WorkingDirectory=/home/pi/SecureDocSystem
ExecStart=/home/pi/SecureDocSystem/venv/bin/python3 raspberry_pi/pi_verify_terminal.py \
  --watch /media/usb/incoming --manifest samples/manifest.json \
  --provenance samples/provenance.json --fullscreen
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now doc-verify.service
```

## Experimental Results

From `py -3 main.py full`:

| Metric | Value |
|--------|-------|
| PSNR | ~21.8 dB |
| Encryption time | ~200 ms |
| Embedding capacity | 128 characters |
| Extraction accuracy | 1.0 |
| False positive rate | 0.0 |
| Attack pass rate | 1.0 |

Attacks tested: compression, cropping, scaling, screenshot simulation, minor edits — all PASS.

Traversal path after transfers: `CollegeXYZ → Abhishek → Rahul → Priya` (provenance chain valid).

## Limitations

- Screenshot robustness is demonstrated against the implemented redistribution simulation, not every real-world camera-display pipeline
- The Pi terminal is not a hardware root of trust (no TPM/HSM) — it verifies using the public key only
- Verification on Pi will be slower than desktop; measure actual timings on your hardware
- Re-run `py -3 main.py full` after transfers to confirm robustness on later-version copies

## Future Work

- DWT + DCT hybrid embedding
- Error-correcting codes and synchronization markers
- Stronger real-world screenshot recovery
- Enhanced web verifier UI
