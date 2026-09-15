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
"""

import sys

GREEN_PIN = 17  # BCM numbering — change to match your wiring
RED_PIN = 27

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
    """

    def __init__(self, green_pin=GREEN_PIN, red_pin=RED_PIN):
        self.green_pin = green_pin
        self.red_pin = red_pin
        self._setup_done = False
        if HARDWARE_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.green_pin, GPIO.OUT)
            GPIO.setup(self.red_pin, GPIO.OUT)
            GPIO.output(self.green_pin, GPIO.LOW)
            GPIO.output(self.red_pin, GPIO.LOW)
            self._setup_done = True

    def set_status(self, authentic):
        if HARDWARE_AVAILABLE and self._setup_done:
            GPIO.output(self.green_pin, GPIO.HIGH if authentic else GPIO.LOW)
            GPIO.output(self.red_pin, GPIO.LOW if authentic else GPIO.HIGH)
        else:
            label = "GREEN (AUTHENTIC)" if authentic else "RED (TAMPERED)"
            print(f"[mock LED] {label}", file=sys.stderr)

    def blink_error(self, times=3):
        """Both LEDs flash together — used for a hard failure (e.g. file
        or manifest missing) rather than a tamper verdict."""
        import time

        for _ in range(times):
            if HARDWARE_AVAILABLE and self._setup_done:
                GPIO.output(self.green_pin, GPIO.HIGH)
                GPIO.output(self.red_pin, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(self.green_pin, GPIO.LOW)
                GPIO.output(self.red_pin, GPIO.LOW)
                time.sleep(0.2)
            else:
                print("[mock LED] BOTH BLINKING (error)", file=sys.stderr)
                time.sleep(0.1)

    def cleanup(self):
        if HARDWARE_AVAILABLE and self._setup_done:
            GPIO.output(self.green_pin, GPIO.LOW)
            GPIO.output(self.red_pin, GPIO.LOW)
            GPIO.cleanup([self.green_pin, self.red_pin])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
