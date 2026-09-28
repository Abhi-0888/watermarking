"""
raspberry_pi/led_test.py — wiring sanity check for the green/red LEDs.

Cycles through four states so you can confirm each LED works independently:
  1. GREEN on  (authentic indicator)
  2. RED on    (tamper indicator)
  3. BOTH on   (error blink indicator)
  4. ALL off

Run from the project root (with the venv active):
    python3 raspberry_pi/led_test.py

On non-Pi hardware the mock path is taken automatically and the states
are printed to stderr, so this is safe to run during development too.

Exit codes:
    0  — completed normally
    1  — unexpected exception
"""

import sys
import time
from pathlib import Path

# Allow running as `python3 raspberry_pi/led_test.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from raspberry_pi.gpio_led import HARDWARE_AVAILABLE, GREEN_PIN, RED_PIN, LedIndicator


_HOLD = 1.0  # seconds per state — long enough to see / photograph


def _print_state(label: str) -> None:
    print(f"[led_test] {label}")


def main() -> None:
    print("[led_test] Starting LED wiring test")
    print(f"[led_test] Hardware GPIO available : {HARDWARE_AVAILABLE}")
    if HARDWARE_AVAILABLE:
        print(f"[led_test] GREEN pin : BCM {GREEN_PIN}")
        print(f"[led_test] RED pin   : BCM {RED_PIN}")
    else:
        print("[led_test] Running in mock mode — states printed to stderr")

    with LedIndicator() as led:
        # ── State 1: GREEN ───────────────────────────────────────────
        _print_state("State 1/4 — GREEN on (authentic)")
        led.set_status(authentic=True)
        time.sleep(_HOLD)

        # ── State 2: RED ─────────────────────────────────────────────
        _print_state("State 2/4 — RED on (tampered)")
        led.set_status(authentic=False)
        time.sleep(_HOLD)

        # ── State 3: BOTH (error blink) ───────────────────────────────
        _print_state("State 3/4 — BOTH blinking (error state, 3 flashes)")
        led.blink_error(times=3)
        time.sleep(_HOLD)

        # ── State 4: ALL off (via cleanup in __exit__) ────────────────
        _print_state("State 4/4 — ALL off (cleanup)")
        # cleanup() is called automatically on __exit__; reset manually
        # here so the "off" state is visually distinct before exit.
        if HARDWARE_AVAILABLE and led._setup_done:
            import RPi.GPIO as _GPIO  # type: ignore
            _GPIO.output(led.green_pin, _GPIO.LOW)
            _GPIO.output(led.red_pin, _GPIO.LOW)
        time.sleep(_HOLD)

    print("[led_test] Done. If LEDs did not respond, check:")
    print("  • Wiring: GPIO17 → 330Ω → GREEN anode → GND")
    print("  •         GPIO27 → 330Ω → RED   anode → GND")
    print("  • GPIO group membership: groups | grep gpio")
    print("  • GPIO library installed: python3 -c \"import RPi.GPIO\"")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[led_test] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
