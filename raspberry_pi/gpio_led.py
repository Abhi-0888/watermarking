"""
Green / red LED status indicator, driven from Raspberry Pi GPIO pins.

The Pi does not implement any new cryptography — it just reflects the
verification verdict computed by verify_document() as a physical signal:
GREEN = authentic, RED = tampered/suspicious.

This module auto-detects whether RPi.GPIO is actually available (i.e.
whether it's running on real Raspberry Pi hardware). If not — for example
while developing/testing on a laptop — it falls back to a console "mock"
that prints the LED state instead of raising an import error, so the rest
of the terminal logic can be developed and unit tested off-device.

Optional buzzer support (Step 7):
    Set BUZZER_PIN to a BCM GPIO number, e.g. 23, to enable a passive or
    active buzzer on that pin.  Leave BUZZER_PIN = None to disable (default).
    When enabled:
      • set_status(authentic=False) fires a short double-beep on tamper.
      • blink_error() fires a triple-beep alongside the LED blinks.
    All buzzer code is fully guarded — if BUZZER_PIN is None the behaviour
    is identical to the original, so gui_verify.py and web_verify.py are
    unaffected.
"""

import sys
import time

GREEN_PIN  = 17   # BCM numbering — change to match your wiring
RED_PIN    = 27   # BCM numbering
BUZZER_PIN = None # Set to a BCM pin number (e.g. 23) to enable buzzer
                  # Leave as None to keep original LED-only behaviour.

try:
    import RPi.GPIO as GPIO  # type: ignore

    HARDWARE_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO = None
    HARDWARE_AVAILABLE = False


class LedIndicator:
    """Usage:
        with LedIndicator() as led:
            led.set_status(authentic=True)

    To enable the buzzer, pass a BCM pin number:
        with LedIndicator(buzzer_pin=23) as led:
            led.set_status(authentic=False)  # beeps on tamper
    """

    def __init__(self, green_pin=GREEN_PIN, red_pin=RED_PIN, buzzer_pin=BUZZER_PIN):
        self.green_pin  = green_pin
        self.red_pin    = red_pin
        self.buzzer_pin = buzzer_pin
        self._setup_done = False

        if HARDWARE_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            GPIO.setup(self.green_pin,  GPIO.OUT)
            GPIO.setup(self.red_pin,    GPIO.OUT)
            GPIO.output(self.green_pin, GPIO.LOW)
            GPIO.output(self.red_pin,   GPIO.LOW)

            if self.buzzer_pin is not None:
                GPIO.setup(self.buzzer_pin, GPIO.OUT)
                GPIO.output(self.buzzer_pin, GPIO.LOW)

            self._setup_done = True

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    def _buzz(self, pattern: list[float]) -> None:
        """Drive the buzzer with a list of (on_secs, off_secs) tuples.
        No-op if buzzer_pin is None or hardware is not available."""
        if not HARDWARE_AVAILABLE or not self._setup_done or self.buzzer_pin is None:
            return
        for on_t, off_t in pattern:
            GPIO.output(self.buzzer_pin, GPIO.HIGH)
            time.sleep(on_t)
            GPIO.output(self.buzzer_pin, GPIO.LOW)
            if off_t > 0:
                time.sleep(off_t)

    def _mock_buzz(self, label: str) -> None:
        """Mock-mode buzzer — prints to stderr like the mock LED."""
        if self.buzzer_pin is not None:
            print(f"[mock BUZZ] {label}", file=sys.stderr)

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def set_status(self, authentic: bool) -> None:
        """Set LEDs (and optionally beep on tamper)."""
        if HARDWARE_AVAILABLE and self._setup_done:
            GPIO.output(self.green_pin, GPIO.HIGH if authentic else GPIO.LOW)
            GPIO.output(self.red_pin,   GPIO.LOW  if authentic else GPIO.HIGH)
            if not authentic:
                # Short double-beep: beep-beep to signal tamper
                self._buzz([(0.15, 0.1), (0.15, 0.0)])
        else:
            label = "GREEN (AUTHENTIC)" if authentic else "RED (TAMPERED)"
            print(f"[mock LED] {label}", file=sys.stderr)
            if not authentic:
                self._mock_buzz("double-beep (tamper)")

    def blink_error(self, times: int = 3) -> None:
        """Both LEDs flash together — used for a hard failure (e.g. file
        or manifest missing) rather than a tamper verdict.
        Also fires a triple-beep when a buzzer pin is configured."""
        for _ in range(times):
            if HARDWARE_AVAILABLE and self._setup_done:
                GPIO.output(self.green_pin, GPIO.HIGH)
                GPIO.output(self.red_pin,   GPIO.HIGH)
                if self.buzzer_pin is not None:
                    GPIO.output(self.buzzer_pin, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(self.green_pin, GPIO.LOW)
                GPIO.output(self.red_pin,   GPIO.LOW)
                if self.buzzer_pin is not None:
                    GPIO.output(self.buzzer_pin, GPIO.LOW)
                time.sleep(0.2)
            else:
                print("[mock LED] BOTH BLINKING (error)", file=sys.stderr)
                if self.buzzer_pin is not None:
                    print("[mock BUZZ] beep (error)", file=sys.stderr)
                time.sleep(0.1)

    def cleanup(self) -> None:
        if HARDWARE_AVAILABLE and self._setup_done:
            GPIO.output(self.green_pin, GPIO.LOW)
            GPIO.output(self.red_pin,   GPIO.LOW)
            pins = [self.green_pin, self.red_pin]
            if self.buzzer_pin is not None:
                GPIO.output(self.buzzer_pin, GPIO.LOW)
                pins.append(self.buzzer_pin)
            GPIO.cleanup(pins)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
