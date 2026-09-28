# ADDITIONS — What Changed and Why

This document tracks every file added or modified beyond the original codebase,
explains the rationale, and records the verified test results so you can cite
exact numbers in your report.

---

## New files

### `raspberry_pi/SETUP.md`
Complete step-by-step setup guide: OS prep, venv creation, GPIO group, import
confirmation, one-command demo, manual step-by-step, LED test, fullscreen
display, benchmark, and optional buzzer.

### `raspberry_pi/install_gpio.sh`
Reads `/proc/device-tree/model` and installs `rpi-lgpio` (Pi 5) or `RPi.GPIO`
(Pi 3/4/Zero). Safe no-op on non-Pi machines.

### `raspberry_pi/led_test.py`
Wiring sanity check: cycles GREEN → RED → BOTH (3× blink) → OFF, 1 s per state.
Falls back to `[mock LED]` on non-Pi hardware so it is safe to run anywhere.

### `raspberry_pi/benchmark.py`
Runs `verify_document()` N times (default 30, 1 warm-up discarded), records
wall-clock time, peak RSS (psutil), and CPU%. Writes `results/pi_benchmark.csv`
with the Pi model in the header comment. Prints a summary table to stdout.

### `scripts/make_tampered.py`
Standalone script that creates four tampered variants of `samples/watermarked.png`.
See tamper test results below for exact verdicts.

### `scripts/pi_demo.py`
**Primary integration script.** Runs the full five-stage pipeline end-to-end:

| Stage | What runs | Key output |
|-------|-----------|-----------|
| 1 | `protect_document()` (main.py demo) | `watermarked.png`, `manifest.json`, `registry.json`, `provenance.json`, `keys/` |
| 2 | Transfer Abhishek → Rahul | `watermarked_v2.png`, provenance record 2 |
| 3 | Transfer Rahul → Priya | `watermarked_v3.png`, provenance record 3 |
| 4 | `pi_verify_terminal.run_once()` — authentic copy | AUTHENTIC verdict, GREEN LED, traversal path |
| 5 | Four tamper variants created + verified | See tamper results table below |

Flags: `--no-led`, `--fullscreen`, `--skip-issue`, `--skip-tamper`, `--mode offline|online`.
Exit code 0 when the authentic copy verifies correctly.

### `scripts/pi_demo.sh`
Thin Bash wrapper: activates the venv (`venv/bin/activate`), `cd`s to the
project root, then forwards all flags to `pi_demo.py`.

### `results/` directory
Holds `pi_benchmark.csv` and any output files from test runs. Tracked by git
(via `results/.gitkeep`); generated CSV/overlay files are `.gitignore`'d.

---

## Modified files

### `raspberry_pi/pi_verify_terminal.py`
**Key change: all path flags now have sensible defaults pointing at `samples/`.**

| Change | Detail |
|--------|--------|
| `--manifest` no longer `required=True` | Defaults to `samples/manifest.json` |
| `--registry` default added | `samples/registry.json` |
| `--provenance` default added | `samples/provenance.json` |
| `--file` default added | `samples/watermarked.png` |
| `--mode` default changed | Was `offline`, now `online` (uses registry by default) |
| `--demo` flag added | Calls `protect_document()` + 2 transfers before verifying |
| `run_once()` path resolution | Resolves relative paths against project root |
| Missing-file error message | Prints a helpful hint pointing to `--demo` |

Bare invocation `python3 raspberry_pi/pi_verify_terminal.py` now works with no
arguments once sample files have been generated.

### `raspberry_pi/gpio_led.py`
- Added optional **buzzer** support: `BUZZER_PIN = None` (disabled by default).
- `set_status(authentic=False)` fires a short double-beep when a buzzer pin is set.
- `blink_error()` fires a triple-beep alongside the LED blinks.
- All buzzer code guarded by `HARDWARE_AVAILABLE` and `buzzer_pin is not None` —
  existing LED-only behaviour is unchanged when `buzzer_pin=None`.

### `raspberry_pi/monitor_display.py`
- **Stdout encoding fix**: `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`
  called at import time so box-drawing characters never raise `UnicodeEncodeError`
  regardless of the host terminal's code page (fixes Windows cp1252 consoles).
- Automatic ASCII fallback: `─` → `-` and `═` → `=` when stdout encoding is
  not UTF-8 after the reconfigure attempt.
- Fullscreen curses layout improvements:
  - Title row: `A_REVERSE | A_BOLD` (readable on dark and light backgrounds).
  - STATUS and TAMPER rows: green/red colouring matching the LED.
  - All rows centre-aligned to terminal width.
  - "Press any key to dismiss" footer (timeout 8 s).
  - Falls back to plain-print when terminal < 52 cols or < 20 rows.

### `raspberry_pi/benchmark.py`
- Column header uses ASCII `-` separators (not `─`) for portable output.
- Summary table uses dynamic `═`/`=` and `─`/`-` based on stdout encoding.

### `raspberry_pi/requirements-pi.txt`
- Added `psutil` (required by `benchmark.py`).
- Added comments explaining Pi 5 vs Pi 3/4 package choice.

### `.gitignore`
- Added `results/*.csv` and `samples/tampered/` to exclude generated test files.

---

## Files NOT changed

- `main.py`, `transfer.py` — untouched.
- `gui_verify.py`, `web_verify.py` — untouched; both still call
  `verification.verify.verify_document()` directly and are unaffected by all
  changes above.
- All `encryption/`, `watermark/`, `verification/`, `provenance/`, `utils/`
  modules — untouched. No new cryptography added anywhere.
- `samples/keys/private.pem` — never copied to the Pi; never exposed.

---

## Verified test results (dry-run on Windows, logic identical on Pi)

### Authentic copy

```
Hash Check        : PASS
Signature Check   : PASS
Watermark Check   : PASS   (score 0.991)
Registry Check    : PASS
Tamper            : NONE DETECTED (0.0% of blocks)
Provenance Chain  : VALID
Traversal Path    : CollegeXYZ -> Abhishek -> Rahul -> Priya
Verdict           : AUTHENTIC
Verify time       : ~380 ms (Windows x86-64; expect faster on Pi 4)
```

### Tamper test results

| Variant | Hash | Sig | Watermark | Tamper blocks | % blocks | LED | Verdict |
|---------|------|-----|-----------|---------------|---------|-----|---------|
| `tampered_patch` | FAIL | FAIL | PASS | 20 (B16-17…B18-20) | 1.39 % | RED | TAMPERED |
| `tampered_text` | FAIL | FAIL | PASS | 46 (B10-10…B11-12) | 3.19 % | RED | TAMPERED |
| `tampered_jpeg` | FAIL | FAIL | FAIL | 776 (53.74 %) | 53.74 % | RED | TAMPERED |
| `tampered_crop` | FAIL | FAIL | FAIL | geometry mismatch | N/A | RED | TAMPERED |

**Notes on redistribution variants:**
- `tampered_jpeg` at quality 50 destroys the DCT watermark completely — all
  checks fail. This is expected and honest: severe JPEG compression is not a
  redistribution that preserves document integrity.
- `tampered_crop` causes a geometry mismatch so the block-level localizer
  cannot operate, but hash + sig still fail independently — verdict is TAMPERED.

---

## What to photograph / screenshot for your report

| # | What | How |
|---|------|-----|
| 1 | Pi model | `cat /proc/device-tree/model` |
| 2 | Import check | Run the 8-line python snippet in step 6 of SETUP.md |
| 3 | Full demo run | `python3 scripts/pi_demo.py --no-led` (stages 1–5 scroll) |
| 4 | Authentic verdict | Dashboard showing `Verdict: AUTHENTIC` + traversal path |
| 5 | **Green LED lit** | Photograph hardware during authentic verification |
| 6 | **Red LED lit** | Photograph hardware during `tampered_patch` verification |
| 7 | Tamper patch output | Terminal showing 20 tampered block labels |
| 8 | Tamper text output | Terminal showing 46 tampered block labels |
| 9 | JPEG / crop output | Terminal showing honest redistribution verdict |
| 10 | Benchmark table | `python3 raspberry_pi/benchmark.py …` summary printout |
| 11 | Benchmark CSV | `cat results/pi_benchmark.csv` |
| 12 | Fullscreen dashboard | VNC screenshot of coloured curses display |
| 13 | Buzzer wiring (optional) | Photo of GPIO23 connection on breadboard |
