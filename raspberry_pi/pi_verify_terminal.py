"""
Raspberry Pi verification terminal.

Runs on the Pi as the lightweight field-verification device.  It does NOT
implement any new cryptography — it simply calls the same verify_document()
pipeline used on the desktop/web verifiers, then:

  - shows the result on the monitor (HDMI console dashboard)
  - drives the green/red LED
  - prints provenance / transfer history and tamper-localization detail

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK START — works with the included sample image, no flags:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # 1. Generate sample files AND verify in one command:
  python3 raspberry_pi/pi_verify_terminal.py --demo

  # 2. If you already ran main.py demo + transfer.py, just verify:
  python3 raspberry_pi/pi_verify_terminal.py

  # Both commands above resolve paths automatically.
  # --mode defaults to "online", --provenance defaults to
  # samples/provenance.json, etc.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXPLICIT USAGE (all flags optional except when using --watch):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Single-shot verify with explicit paths:
  python3 raspberry_pi/pi_verify_terminal.py \\
      --file     samples/watermarked.png \\
      --manifest samples/manifest.json \\
      --registry samples/registry.json \\
      --provenance samples/provenance.json \\
      --mode online

  # Watch a folder (kiosk / USB inbox mode):
  python3 raspberry_pi/pi_verify_terminal.py \\
      --watch /media/usb/incoming \\
      --manifest samples/manifest.json \\
      --provenance samples/provenance.json

  # HDMI kiosk dashboard (curses fullscreen):
  python3 raspberry_pi/pi_verify_terminal.py --fullscreen
"""

import argparse
import sys
import time
from pathlib import Path

# Allow running as `python3 raspberry_pi/pi_verify_terminal.py` from any cwd
_THIS_DIR   = Path(__file__).resolve().parent        # .../raspberry_pi/
_ROOT_DIR   = _THIS_DIR.parent                       # .../SecureDocSystem/
_SAMPLES    = _ROOT_DIR / "samples"

sys.path.insert(0, str(_ROOT_DIR))

from raspberry_pi.gpio_led import LedIndicator
from raspberry_pi.monitor_display import print_dashboard, show_fullscreen_dashboard
from verification.verify import verify_document


# ──────────────────────────────────────────────────────────────────────────────
# Default sample paths (used when no explicit flags are given)
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_FILE       = str(_SAMPLES / "watermarked.png")
_DEFAULT_MANIFEST   = str(_SAMPLES / "manifest.json")
_DEFAULT_REGISTRY   = str(_SAMPLES / "registry.json")
_DEFAULT_PROVENANCE = str(_SAMPLES / "provenance.json")


# ──────────────────────────────────────────────────────────────────────────────
# Demo helper — generate sample artefacts then verify
# ──────────────────────────────────────────────────────────────────────────────

def _run_demo_setup():
    """
    Runs the full issuance + transfer chain so that all sample files exist
    before we attempt verification:
      1. main.py demo  (CollegeXYZ → Abhishek, v1)
      2. transfer.py   (Abhishek → Rahul, v2)
      3. transfer.py   (Rahul → Priya, v3)

    Importing these at module level is intentionally avoided so that
    non-demo invocations don't pay the import cost of cv2 / numpy before
    the terminal even starts.
    """
    print("\n" + "━" * 58)
    print("  [demo-setup] Generating sample artefacts …")
    print("━" * 58)

    # ── Phase A: issue document ───────────────────────────────────────
    print("\n[demo-setup] Phase A — Issue document (main.py demo)")
    # Import protect_document lazily so the Pi terminal is light when used normally.
    # Pop any stale cached module in case this is called more than once.
    import sys as _sys
    _sys.modules.pop("main", None)

    import main as _main
    _main.protect_document(run_full_evaluation=False, present_mode=False)

    # ── Phase B: transfers ────────────────────────────────────────────
    print("\n[demo-setup] Phase B — Transfer Abhishek → Rahul")
    from transfer import transfer_document
    transfer_document(
        document_id="DOC-2026-001",
        sender="Abhishek",
        receiver="Rahul",
    )

    print("\n[demo-setup] Phase C — Transfer Rahul → Priya")
    transfer_document(
        document_id="DOC-2026-001",
        sender="Rahul",
        receiver="Priya",
    )

    print("\n[demo-setup] ✓ Sample artefacts ready.\n")
    print("  Protected file : " + _DEFAULT_FILE)
    print("  Manifest       : " + _DEFAULT_MANIFEST)
    print("  Registry       : " + _DEFAULT_REGISTRY)
    print("  Provenance     : " + _DEFAULT_PROVENANCE)
    print()


# ──────────────────────────────────────────────────────────────────────────────
# Core verification helpers
# ──────────────────────────────────────────────────────────────────────────────

def run_once(file_path, manifest_path, mode, registry_path, provenance_path,
             fullscreen=False, led=None):
    """
    Verify one file and display the result.

    Returns the full report dict on success, or None if verification could
    not run (missing file, corrupt manifest, etc.).
    """
    # Resolve relative paths against the project root so callers can pass
    # either absolute paths or short relative ones (e.g. "samples/watermarked.png").
    def _abs(p):
        if p is None:
            return None
        path = Path(p)
        return str(path if path.is_absolute() else _ROOT_DIR / path)

    file_path      = _abs(file_path)
    manifest_path  = _abs(manifest_path)
    registry_path  = _abs(registry_path)
    provenance_path= _abs(provenance_path)

    # Guard: print a clear message if key files are missing
    missing = [p for p in (file_path, manifest_path) if p and not Path(p).exists()]
    if missing:
        for p in missing:
            print(f"[pi-terminal] File not found: {p}", file=sys.stderr)
        hint = ("Run `python3 raspberry_pi/pi_verify_terminal.py --demo` to generate "
                "sample files first, or pass --file / --manifest explicitly.")
        print(f"[pi-terminal] Hint: {hint}", file=sys.stderr)
        if led is not None:
            led.blink_error()
        return None

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

    tamper_report    = report.get("tamper_localization", {})
    provenance_entry = report.get("provenance")
    path_list        = report.get("traversal_path", [])

    if fullscreen:
        show_fullscreen_dashboard(report, tamper_report, provenance_entry, path_list)
    else:
        print_dashboard(report, tamper_report, provenance_entry, path_list)

    verdict = "AUTHENTIC" if report["authentic"] else "SUSPICIOUS / TAMPERED"
    print(f"[pi-terminal] Verdict           : {verdict}")
    print(f"[pi-terminal] Verification time : {elapsed_ms} ms")

    if led is not None:
        led.set_status(report["authentic"])

    return report


def watch_folder(folder, manifest_path, mode, registry_path, provenance_path,
                 fullscreen, led, poll_seconds=2):
    seen   = set()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    print(f"[pi-terminal] Watching {folder} for new documents (Ctrl+C to stop) …")
    try:
        while True:
            for candidate in sorted(folder.glob("*.png")) + sorted(folder.glob("*.jpg")):
                if candidate in seen:
                    continue
                seen.add(candidate)
                print(f"\n[pi-terminal] New document detected: {candidate}")
                run_once(str(candidate), manifest_path, mode, registry_path,
                         provenance_path, fullscreen, led)
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        print("\n[pi-terminal] Stopped.")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Raspberry Pi document verification terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Quick start (auto-generates sample files then verifies):\n"
            "  python3 raspberry_pi/pi_verify_terminal.py --demo\n\n"
            "Plain verify (sample files already generated):\n"
            "  python3 raspberry_pi/pi_verify_terminal.py\n\n"
            "All path flags have sensible defaults pointing at samples/."
        ),
    )

    # ── source / mode ─────────────────────────────────────────────────
    parser.add_argument(
        "--demo", action="store_true",
        help=(
            "Auto-generate all sample artefacts (main.py demo + 2 transfers) "
            "then verify.  Use this on a fresh checkout or after deleting samples/."
        ),
    )
    parser.add_argument(
        "--file", dest="file_path",
        default=_DEFAULT_FILE,
        help=f"Protected file to verify (default: {_DEFAULT_FILE})",
    )
    parser.add_argument(
        "--watch", dest="watch_folder",
        help="Folder to watch for new documents (loop / kiosk mode)",
    )

    # ── manifest / registry / provenance ──────────────────────────────
    parser.add_argument(
        "--manifest", dest="manifest_path",
        default=_DEFAULT_MANIFEST,
        help=f"Manifest JSON (default: {_DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--registry", dest="registry_path",
        default=_DEFAULT_REGISTRY,
        help=f"Registry JSON for online mode (default: {_DEFAULT_REGISTRY})",
    )
    parser.add_argument(
        "--provenance", dest="provenance_path",
        default=_DEFAULT_PROVENANCE,
        help=f"Provenance chain JSON (default: {_DEFAULT_PROVENANCE})",
    )

    # ── misc ──────────────────────────────────────────────────────────
    parser.add_argument(
        "--mode", default="online", choices=["offline", "online"],
        help="Verification mode (default: online)",
    )
    parser.add_argument(
        "--fullscreen", action="store_true",
        help="Use curses HDMI kiosk display (fallback: plain print)",
    )
    parser.add_argument(
        "--no-led", action="store_true",
        help="Disable GPIO/LED output (useful on non-Pi hardware or bench testing)",
    )

    args = parser.parse_args()

    # ── Demo setup: generate artefacts first ──────────────────────────
    if args.demo:
        _run_demo_setup()

    # ── LED init ──────────────────────────────────────────────────────
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
