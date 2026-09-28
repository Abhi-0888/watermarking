"""
scripts/pi_demo.py — End-to-end Raspberry Pi integration demo.

Runs the complete SecureDocSystem pipeline in one command so you can see
every component working together on real sample files:

  Stage 1  — Issue the document (main.py demo)
             CollegeXYZ issues watermarked copy v1 to Abhishek.
  Stage 2  — Transfer 1: Abhishek → Rahul (v2)
  Stage 3  — Transfer 2: Rahul → Priya  (v3)
  Stage 4  — Pi terminal: verify the authentic copy
             Expected: AUTHENTIC  •  GREEN LED  •  chain VALID
             Traversal: CollegeXYZ → Abhishek → Rahul → Priya
  Stage 5  — Tamper variants: create 4 attacked copies and verify each
             Shows honest LED colour, tamper blocks, and verdict.

Usage (from project root, venv active):
    python3 scripts/pi_demo.py                      # plain-print mode
    python3 scripts/pi_demo.py --fullscreen         # curses kiosk display
    python3 scripts/pi_demo.py --no-led             # skip GPIO
    python3 scripts/pi_demo.py --skip-tamper        # stages 1-4 only
    python3 scripts/pi_demo.py --skip-issue         # skip stage 1-3 (files already exist)

All paths resolve relative to the project root automatically.
"""

import argparse
import sys
import time
from pathlib import Path

# ── project root on sys.path ──────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent   # .../SecureDocSystem
sys.path.insert(0, str(_ROOT))

_SAMPLES   = _ROOT / "samples"
_TAMPERED  = _SAMPLES / "tampered"
_RESULTS   = _ROOT / "results"

_PROTECTED_FILE = _SAMPLES / "watermarked.png"
_MANIFEST       = _SAMPLES / "manifest.json"
_REGISTRY       = _SAMPLES / "registry.json"
_PROVENANCE     = _SAMPLES / "provenance.json"


# ── pretty-print helpers ──────────────────────────────────────────────────────

_W = 62   # banner width

# Use ASCII when stdout can't handle box-drawing (e.g. Windows cp1252).
_ENC        = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
_UNICODE_OK = _ENC.lower().replace("-", "") in ("utf8", "utf16", "utf32")
_H  = "═" if _UNICODE_OK else "="
_S  = "─" if _UNICODE_OK else "-"


def _banner(title: str) -> None:
    print("\n" + _H * _W)
    print(f"  {title}")
    print(_H * _W)


def _step(msg: str) -> None:
    print(f"\n  ▶  {msg}")


def _ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠  {msg}", file=sys.stderr)


def _fail(msg: str) -> None:
    print(f"  ✗  {msg}", file=sys.stderr)


# ── Stage helpers ─────────────────────────────────────────────────────────────

def stage_issue() -> None:
    """Stage 1: issue the protected document (main.py demo pipeline)."""
    _banner("STAGE 1 — Issue document  (CollegeXYZ → Abhishek v1)")

    # Lazy import so non-demo paths don't load cv2/numpy prematurely
    import main as _main  # noqa: PLC0415
    _main.protect_document(run_full_evaluation=False, present_mode=False)

    _ok(f"watermarked.png  → {_PROTECTED_FILE}")
    _ok(f"manifest.json    → {_MANIFEST}")
    _ok(f"registry.json    → {_REGISTRY}")
    _ok(f"provenance.json  → {_PROVENANCE}")


def stage_transfer(sender: str, receiver: str) -> None:
    """Stages 2 & 3: authorised transfer."""
    _banner(f"STAGE — Transfer  {sender} → {receiver}")

    from transfer import transfer_document  # noqa: PLC0415
    result = transfer_document(
        document_id="DOC-2026-001",
        sender=sender,
        receiver=receiver,
    )
    entry = result["provenance_entry"]
    _ok(f"New copy: {result['protected_file']}")
    _ok(f"Transfer count: {entry['transfer_count']}  "
        f"Current holder: {entry['current_holder']}")


def stage_verify_authentic(fullscreen: bool, led, mode: str) -> bool:
    """Stage 4: verify the authentic (untampered) latest copy on the Pi terminal."""
    _banner("STAGE 4 — Pi terminal: verify AUTHENTIC copy")

    from raspberry_pi.pi_verify_terminal import run_once  # noqa: PLC0415

    report = run_once(
        file_path       = str(_PROTECTED_FILE),
        manifest_path   = str(_MANIFEST),
        mode            = mode,
        registry_path   = str(_REGISTRY),
        provenance_path = str(_PROVENANCE),
        fullscreen      = fullscreen,
        led             = led,
    )

    if report is None:
        _fail("Verification returned None — check the error above.")
        return False

    authentic = report["authentic"]
    traversal = " → ".join(report.get("traversal_path", []))
    chain_ok  = report.get("provenance_chain_valid")

    print()
    _ok(f"Verdict           : {'AUTHENTIC ✓' if authentic else 'TAMPERED ✗'}")
    _ok(f"Traversal path    : {traversal or 'Not available'}")
    _ok(f"Provenance chain  : {'VALID' if chain_ok else 'BROKEN / N/A'}")

    expected_path = "CollegeXYZ → Abhishek → Rahul → Priya"
    if traversal and traversal != expected_path:
        _warn(f"Expected: {expected_path}")
        _warn(f"Got     : {traversal}")
    elif traversal == expected_path:
        _ok("Traversal path matches expected ✓")

    return authentic


def stage_tamper_tests(fullscreen: bool, led, mode: str) -> list[dict]:
    """
    Stage 5: create 4 tampered variants and run each through the Pi terminal.
    Returns a list of result dicts (one per variant).
    """
    _banner("STAGE 5 — Tamper / attack variants")

    # ── 5a: create the variants ───────────────────────────────────────
    _step("Creating tampered variants …")

    # Import the helpers directly so we don't re-parse argparse
    _TAMPERED.mkdir(parents=True, exist_ok=True)

    import cv2  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    def _load(path):
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"Cannot read: {path}")
        return img

    img = _load(_PROTECTED_FILE)
    h, w = img.shape

    # (a) Painted patch
    patch_path = _TAMPERED / "tampered_patch.png"
    out = img.copy()
    cy, cx = h // 2, w // 2
    out[cy - 40 : cy + 20, cx - 30 : cx + 30] = 128
    cv2.imwrite(str(patch_path), out)
    _ok(f"tampered_patch.png  — 60×60 grey patch at centre")

    # (b) Text overlay
    text_path = _TAMPERED / "tampered_text.png"
    out = img.copy()
    colour = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
    cv2.putText(colour, "COPY",        (w // 4, h // 3),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)
    cv2.putText(colour, "UNVERIFIED",  (w // 4, h // 3 + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(text_path), cv2.cvtColor(colour, cv2.COLOR_BGR2GRAY))
    _ok(f"tampered_text.png   — 'COPY UNVERIFIED' text overlay")

    # (c) JPEG compression (redistribution attack)
    jpeg_path = _TAMPERED / "tampered_jpeg.png"
    ok_enc, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    if ok_enc:
        degraded = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
        cv2.imwrite(str(jpeg_path), degraded)
        _ok(f"tampered_jpeg.png   — JPEG quality=50 round-trip (redistribution)")
    else:
        _warn("JPEG encode failed — skipping compression variant")
        jpeg_path = None

    # (d) Crop (redistribution attack)
    margin    = 32
    crop_path = _TAMPERED / "tampered_crop.png"
    if h > 2 * margin and w > 2 * margin:
        cropped = img[margin : h - margin, margin : w - margin]
        cv2.imwrite(str(crop_path), cropped)
        _ok(f"tampered_crop.png   — {margin}px crop each side → {cropped.shape[1]}×{cropped.shape[0]}")
    else:
        _warn("Image too small to crop — skipping crop variant")
        crop_path = None

    # ── 5b: verify each variant ───────────────────────────────────────
    from raspberry_pi.pi_verify_terminal import run_once  # noqa: PLC0415

    variants = [
        ("tampered_patch", patch_path, "deliberate edit → expect TAMPERED"),
        ("tampered_text",  text_path,  "deliberate edit → expect TAMPERED"),
        ("tampered_jpeg",  jpeg_path,  "redistribution → honest: may PASS"),
        ("tampered_crop",  crop_path,  "redistribution → honest: geometry mismatch"),
    ]

    results = []
    for name, vpath, note in variants:
        if vpath is None:
            results.append({"variant": name, "skipped": True})
            continue

        _banner(f"STAGE 5 — Verifying: {name}")
        print(f"  Note: {note}")
        time.sleep(0.3)   # small pause so LED state is visible if wired up

        report = run_once(
            file_path       = str(vpath),
            manifest_path   = str(_MANIFEST),
            mode            = mode,
            registry_path   = str(_REGISTRY),
            provenance_path = str(_PROVENANCE),
            fullscreen      = fullscreen,
            led             = led,
        )

        if report is None:
            results.append({"variant": name, "error": True})
            continue

        authentic      = report["authentic"]
        tamper_report  = report.get("tamper_localization", {})
        blocks         = tamper_report.get("block_labels", [])
        supported      = tamper_report.get("supported", False)
        geometry_ok    = supported or (tamper_report.get("reason", "") == "")

        summary = {
            "variant"         : name,
            "authentic"       : authentic,
            "verdict"         : "AUTHENTIC" if authentic else "SUSPICIOUS / TAMPERED",
            "led_colour"      : "GREEN" if authentic else "RED",
            "tamper_supported": supported,
            "tamper_blocks"   : blocks[:6],
            "geometry_match"  : geometry_ok,
            "issues"          : report.get("issues", []),
        }
        results.append(summary)

        # Print summary line
        led_sym = "🟢" if authentic else "🔴"
        blk_str = (", ".join(blocks[:6])) if blocks else ("N/A" if not supported else "NONE")
        print(f"\n  {led_sym} LED  |  Verdict: {summary['verdict']}")
        print(f"     Tamper blocks : {blk_str}")
        if summary["issues"]:
            for iss in summary["issues"]:
                print(f"     Issue         : {iss}")

    return results


# ── Final summary ─────────────────────────────────────────────────────────────

def _print_final_summary(authentic_ok: bool, tamper_results: list[dict]) -> None:
    _banner("DEMO COMPLETE — Summary")

    w1, w2, w3, w4 = 20, 12, 8, 30
    header = f"  {'Variant':<{w1}} {'Verdict':<{w2}} {'LED':<{w4}}"
    sep    = "  " + _S * (w1 + w2 + w3 + w4)

    print(header)
    print(sep)

    # Authentic copy row
    auth_str = "AUTHENTIC" if authentic_ok else "TAMPERED (?)"
    led_str  = "GREEN ✓"  if authentic_ok else "RED ✗"
    print(f"  {'authentic copy':<{w1}} {auth_str:<{w2}} {led_str}")

    # Tamper rows
    for r in tamper_results:
        name    = r["variant"]
        if r.get("skipped"):
            print(f"  {name:<{w1}} {'skipped':<{w2}}")
            continue
        if r.get("error"):
            print(f"  {name:<{w1}} {'ERROR':<{w2}}")
            continue
        verdict = r["verdict"]
        led_col = r["led_colour"]
        blocks  = r["tamper_blocks"]
        blk_str = ", ".join(blocks) if blocks else ("geometry mismatch" if not r["geometry_match"] else "none")
        print(f"  {name:<{w1}} {verdict:<{w2}} {led_col}  |  blocks: {blk_str}")

    print(sep)
    print()
    print("  Expected behaviour:")
    print("    tampered_patch  → RED  (painted patch — deliberate localised edit)")
    print("    tampered_text   → RED  (text overlay   — deliberate localised edit)")
    print("    tampered_jpeg   → may be GREEN or RED  (redistribution, not edit)")
    print("    tampered_crop   → RED  (geometry change — hash + sig both fail)")
    print()
    print("  Photograph for report:")
    print("    • Green LED lit during authentic-copy verification")
    print("    • Red LED lit during tampered_patch or tampered_text verification")
    print("    • Terminal output showing traversal path for the authentic copy")
    print("    • Terminal output showing tamper block labels for patch/text variants")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="End-to-end Pi integration demo: issue → transfer → verify → tamper test"
    )
    parser.add_argument(
        "--fullscreen", action="store_true",
        help="Use curses HDMI kiosk display for each verification step",
    )
    parser.add_argument(
        "--no-led", action="store_true",
        help="Disable GPIO/LED (safe on non-Pi hardware)",
    )
    parser.add_argument(
        "--skip-issue", action="store_true",
        help="Skip stages 1-3 (document already issued and transferred)",
    )
    parser.add_argument(
        "--skip-tamper", action="store_true",
        help="Skip stage 5 (tamper variant tests)",
    )
    parser.add_argument(
        "--mode", default="online", choices=["offline", "online"],
        help="Verification mode (default: online)",
    )
    args = parser.parse_args()

    # ── LED init ──────────────────────────────────────────────────────
    from raspberry_pi.gpio_led import LedIndicator  # noqa: PLC0415
    led = None if args.no_led else LedIndicator()

    authentic_ok   = False
    tamper_results = []

    try:
        # ── Stages 1-3: issue + transfer ─────────────────────────────
        if not args.skip_issue:
            stage_issue()
            stage_transfer("Abhishek", "Rahul")
            stage_transfer("Rahul",    "Priya")
        else:
            # Verify required files exist before attempting verification
            missing = [p for p in (_PROTECTED_FILE, _MANIFEST) if not p.exists()]
            if missing:
                for p in missing:
                    _fail(f"Missing: {p}")
                _fail("Run without --skip-issue to generate sample files first.")
                sys.exit(1)
            _ok("Skipping issue/transfer stages (files already present).")

        # ── Stage 4: authentic verification ──────────────────────────
        authentic_ok = stage_verify_authentic(args.fullscreen, led, args.mode)

        # ── Stage 5: tamper tests ─────────────────────────────────────
        if not args.skip_tamper:
            tamper_results = stage_tamper_tests(args.fullscreen, led, args.mode)

    finally:
        if led is not None:
            led.cleanup()

    # ── Summary ───────────────────────────────────────────────────────
    _print_final_summary(authentic_ok, tamper_results)

    # Exit code: 0 if authentic copy verified correctly, 1 otherwise
    sys.exit(0 if authentic_ok else 1)


if __name__ == "__main__":
    main()
