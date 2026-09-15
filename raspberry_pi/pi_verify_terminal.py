"""
Raspberry Pi verification terminal.

Runs on the Pi as the lightweight field-verification device. It does NOT
implement any new cryptography — it simply calls the same verify_document()
pipeline used on the desktop/web verifiers, then:

  - shows the result on the monitor (HDMI console dashboard)
  - drives the green/red LED
  - prints provenance / transfer history and tamper-localization detail

Usage (single shot):
    python raspberry_pi/pi_verify_terminal.py \
        --file samples/watermarked.png \
        --manifest samples/manifest.json \
        --registry samples/registry.json \
        --provenance samples/provenance.json \
        --mode online

Usage (watch a folder, e.g. a USB drive or an inbox folder, and verify
every new image dropped into it — handy for a kiosk-style terminal):
    python raspberry_pi/pi_verify_terminal.py --watch /media/usb/incoming \
        --manifest samples/manifest.json --provenance samples/provenance.json
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `verification`, `provenance` etc. import

from raspberry_pi.gpio_led import LedIndicator
from raspberry_pi.monitor_display import print_dashboard, show_fullscreen_dashboard
from verification.verify import verify_document


def run_once(file_path, manifest_path, mode, registry_path, provenance_path, fullscreen=False, led=None):
    t0 = time.perf_counter()
    try:
        report = verify_document(
            file_path,
            manifest_path,
            mode=mode,
            registry_path=registry_path,
            provenance_path=provenance_path,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"[pi-terminal] verification could not run: {exc}", file=sys.stderr)
        if led is not None:
            led.blink_error()
        return None
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    tamper_report = report.get("tamper_localization", {})
    provenance_entry = report.get("provenance")
    traversal_path = report.get("traversal_path", [])

    if fullscreen:
        show_fullscreen_dashboard(report, tamper_report, provenance_entry, traversal_path)
    else:
        print_dashboard(report, tamper_report, provenance_entry, traversal_path)

    print(f"[pi-terminal] verification time: {elapsed_ms} ms")

    if led is not None:
        led.set_status(report["authentic"])

    return report


def watch_folder(folder, manifest_path, mode, registry_path, provenance_path, fullscreen, led, poll_seconds=2):
    seen = set()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    print(f"[pi-terminal] watching {folder} for new documents (Ctrl+C to stop)...")
    try:
        while True:
            for candidate in sorted(folder.glob("*.png")) + sorted(folder.glob("*.jpg")):
                if candidate in seen:
                    continue
                seen.add(candidate)
                print(f"\n[pi-terminal] new document detected: {candidate}")
                run_once(str(candidate), manifest_path, mode, registry_path, provenance_path, fullscreen, led)
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        print("\n[pi-terminal] stopped.")


def main():
    parser = argparse.ArgumentParser(description="Raspberry Pi document verification terminal")
    parser.add_argument("--file", dest="file_path", help="Protected file to verify (single-shot mode)")
    parser.add_argument("--watch", dest="watch_folder", help="Folder to watch for new documents (loop mode)")
    parser.add_argument("--manifest", dest="manifest_path", required=True)
    parser.add_argument("--registry", dest="registry_path")
    parser.add_argument("--provenance", dest="provenance_path")
    parser.add_argument("--mode", default="offline", choices=["offline", "online"])
    parser.add_argument("--fullscreen", action="store_true", help="Use curses HDMI kiosk display")
    parser.add_argument("--no-led", action="store_true", help="Disable GPIO/LED output (e.g. bench testing)")
    args = parser.parse_args()

    led = None if args.no_led else LedIndicator()
    try:
        if args.watch_folder:
            watch_folder(
                args.watch_folder,
                args.manifest_path,
                args.mode,
                args.registry_path,
                args.provenance_path,
                args.fullscreen,
                led,
            )
        else:
            if not args.file_path:
                raise SystemExit("Provide --file for single-shot mode or --watch for loop mode.")
            run_once(
                args.file_path,
                args.manifest_path,
                args.mode,
                args.registry_path,
                args.provenance_path,
                args.fullscreen,
                led,
            )
    finally:
        if led is not None:
            led.cleanup()


if __name__ == "__main__":
    main()
