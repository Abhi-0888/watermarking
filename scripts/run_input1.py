"""
scripts/run_input1.py — Full pipeline on samples/input1.jpg (DOC-2026-002).

Runs the complete SecureDocSystem pipeline on input1.jpg:
  Stage 1  — Issue document (CollegeXYZ → Abhishek, v1)
  Stage 2  — Transfer: Abhishek → Rahul (v2)
  Stage 3  — Transfer: Rahul → Priya (v3)
  Stage 4  — Pi terminal: verify the authentic copy
  Stage 5  — Tamper variants: create 4 attacked copies and verify each

All output files use _doc2 suffix / DOC-2026-002 ID to avoid overwriting
the existing input.png results.

Usage (from project root, venv active):
    python3 scripts/run_input1.py
    python3 scripts/run_input1.py --no-led
    python3 scripts/run_input1.py --skip-tamper
    python3 scripts/run_input1.py --skip-issue    # reuse already-generated files
"""

import argparse
import datetime
import shutil
import sys
import time
from pathlib import Path

_ROOT    = Path(__file__).resolve().parent.parent
_SAMPLES = _ROOT / "samples"
_KEYS    = _SAMPLES / "keys2"           # separate key dir for DOC-2026-002
_TAMPERED = _SAMPLES / "tampered2"

sys.path.insert(0, str(_ROOT))

# ── per-document file paths ───────────────────────────────────────────────────
INPUT_FILE      = _SAMPLES / "input1.png"      # colour PNG converted from input1.jpg
ENCRYPTED_FILE  = _SAMPLES / "encrypted2.bin"
DECRYPTED_FILE  = _SAMPLES / "decrypted2.png"
PROTECTED_FILE  = _SAMPLES / "watermarked2.png"
MANIFEST_FILE   = _SAMPLES / "manifest2.json"
REGISTRY_FILE   = _SAMPLES / "registry2.json"
PROVENANCE_FILE = _SAMPLES / "provenance2.json"

DOC_ID          = "DOC-2026-002"
ISSUER_ID       = "CollegeXYZ"

# ── helpers ───────────────────────────────────────────────────────────────────
_W = 62

import os as _os
_ENC      = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
_UNICODE  = _ENC.lower().replace("-", "") in ("utf8", "utf16", "utf32")
_H        = "=" if not _UNICODE else "\u2550"
_S        = "-" if not _UNICODE else "\u2500"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _UNICODE = True
        _H = "\u2550"; _S = "\u2500"
    except Exception:
        pass


def _banner(title):
    print(f"\n{_H*_W}\n  {title}\n{_H*_W}")

def _ok(msg):   print(f"  \u2713  {msg}")
def _step(msg): print(f"\n  \u25b6  {msg}")
def _warn(msg): print(f"  \u26a0  {msg}", file=sys.stderr)
def _fail(msg): print(f"  \u2717  {msg}", file=sys.stderr)


# ── Stage 1: Issue ────────────────────────────────────────────────────────────

def stage_issue():
    _banner(f"STAGE 1 \u2014 Issue document  ({ISSUER_ID} \u2192 Abhishek v1)")

    import cv2
    import numpy as np

    # Ensure input1.png exists (convert from jpg if needed)
    if not INPUT_FILE.exists():
        jpg = _SAMPLES / "input1.jpg"
        if not jpg.exists():
            _fail(f"Neither input1.png nor input1.jpg found in {_SAMPLES}")
            sys.exit(1)
        img = cv2.imread(str(jpg))
        cv2.imwrite(str(INPUT_FILE), img)
        _ok(f"Converted input1.jpg -> input1.png  ({img.shape[1]}x{img.shape[0]})")

    # Read image properties
    img_gray = cv2.imread(str(INPUT_FILE), cv2.IMREAD_GRAYSCALE)
    h, w = img_gray.shape
    _ok(f"Source image : {w}x{h} px")

    # Lazy imports of pipeline modules
    from encryption.aes import decrypt_file, encrypt_file, generate_key
    from encryption.rsa import decrypt_key, encrypt_key, generate_keys, save_keys
    from provenance.chain import init_document as init_provenance
    from utils.metrics import measure_encryption_time
    from verification.package import build_manifest, update_registry, write_manifest
    from verification.tamper_localization import attach_block_descriptors
    from watermark.embed import embed_watermark

    _step("Phase 1: Hybrid encryption")
    aes_key = generate_key()
    private_key, public_key = generate_keys()
    _KEYS.mkdir(parents=True, exist_ok=True)
    save_keys(private_key, public_key, str(_KEYS))
    encrypted_aes_key = encrypt_key(aes_key, public_key)
    decrypted_aes_key = decrypt_key(encrypted_aes_key, private_key)
    _, enc_ms = measure_encryption_time(encrypt_file, str(INPUT_FILE), str(ENCRYPTED_FILE), decrypted_aes_key)
    decrypt_file(str(ENCRYPTED_FILE), str(DECRYPTED_FILE), decrypted_aes_key)
    _ok(f"Encrypted -> {ENCRYPTED_FILE.name}  ({enc_ms:.0f} ms)")

    _step("Phase 2: Invisible watermarking")
    version   = 1
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wm_text   = (f"ISS:{ISSUER_ID}|SRC:{ISSUER_ID}|RCV:Abhishek|"
                 f"DOC:{DOC_ID}|VER:{version}|TS:{timestamp}")
    embed_info = embed_watermark(str(DECRYPTED_FILE), str(PROTECTED_FILE), wm_text)
    _ok(f"Protected file : {PROTECTED_FILE.name}  (redundancy {embed_info['redundancy']}x)")

    _step("Phase 3: Signature + manifest")
    from utils.hash import generate_hash, sign_document, signature_to_text
    manifest = build_manifest(
        original_file       = str(INPUT_FILE),
        protected_file      = str(PROTECTED_FILE),
        watermark_text      = wm_text,
        private_key         = private_key,
        public_key          = public_key,
        issuer_id           = ISSUER_ID,
        receiver_identity   = "Abhishek",
        document_id         = DOC_ID,
        timestamp           = timestamp,
        encrypted_aes_key   = encrypted_aes_key,
        image_shape         = cv2.imread(str(DECRYPTED_FILE), cv2.IMREAD_GRAYSCALE).shape,
    )
    manifest["sender_identity"] = ISSUER_ID
    manifest["version"]         = version
    attach_block_descriptors(manifest, str(PROTECTED_FILE))
    write_manifest(str(MANIFEST_FILE), manifest)
    update_registry(str(REGISTRY_FILE), manifest)
    init_provenance(
        str(PROVENANCE_FILE),
        document_id   = DOC_ID,
        issuer_id     = ISSUER_ID,
        initial_holder= "Abhishek",
        protected_hash= manifest["protected_hash"],
        version       = version,
        timestamp     = timestamp,
    )
    _ok(f"Manifest   : {MANIFEST_FILE.name}")
    _ok(f"Registry   : {REGISTRY_FILE.name}")
    _ok(f"Provenance : {PROVENANCE_FILE.name}")
    _ok(f"Keys       : {_KEYS}/")

    _step("Phase 4: Offline verification (self-check)")
    from verification.verify import verify_document
    rpt = verify_document(str(PROTECTED_FILE), str(MANIFEST_FILE), mode="offline")
    _ok(f"Hash: {'PASS' if rpt['hash_valid'] else 'FAIL'}  "
        f"Sig: {'PASS' if rpt['signature_valid'] else 'FAIL'}  "
        f"WM: {'PASS' if rpt['watermark_valid'] else 'FAIL'}  "
        f"Score: {rpt['watermark_confidence']:.3f}")

    return manifest


# ── Stage 2/3: Transfer ───────────────────────────────────────────────────────

def stage_transfer(sender, receiver):
    _banner(f"STAGE \u2014 Transfer  {sender} \u2192 {receiver}")

    import cv2
    from encryption.rsa import load_keys
    from main import create_watermark_text
    from provenance.chain import add_transfer, get_document as get_prov
    from utils.hash import generate_hash, sign_document, signature_to_text
    from verification.package import update_registry, write_manifest
    from verification.tamper_localization import attach_block_descriptors
    from watermark.embed import embed_watermark

    import json
    with open(MANIFEST_FILE, encoding="utf-8") as fh:
        manifest = json.load(fh)

    private_key, public_key = load_keys(str(_KEYS))
    new_version = manifest.get("version", 1) + 1
    timestamp   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wm_text     = create_watermark_text(ISSUER_ID, sender, receiver, DOC_ID, new_version, timestamp)

    versioned   = _SAMPLES / f"watermarked2_v{new_version}.png"
    embed_watermark(str(PROTECTED_FILE), str(versioned), wm_text)
    shutil.copyfile(versioned, PROTECTED_FILE)
    _ok(f"New copy : {versioned.name}")

    protected_hash = generate_hash(str(PROTECTED_FILE))
    signature      = sign_document(str(PROTECTED_FILE), private_key)

    manifest["watermark_text"]  = wm_text
    manifest["protected_hash"]  = protected_hash
    manifest["signature_b64"]   = signature_to_text(signature)
    manifest["sender_identity"] = sender
    manifest["receiver_identity"] = receiver
    manifest["version"]         = new_version
    manifest["timestamp"]       = timestamp
    manifest["image_shape"]     = list(cv2.imread(str(PROTECTED_FILE), cv2.IMREAD_GRAYSCALE).shape)
    attach_block_descriptors(manifest, str(PROTECTED_FILE))

    versioned_manifest = _SAMPLES / f"manifest2_v{new_version}.json"
    write_manifest(str(versioned_manifest), manifest)
    write_manifest(str(MANIFEST_FILE), manifest)

    entry = add_transfer(
        str(PROVENANCE_FILE),
        document_id    = DOC_ID,
        sender         = sender,
        receiver       = receiver,
        version        = new_version,
        protected_hash = protected_hash,
        timestamp      = timestamp,
    )
    update_registry(str(REGISTRY_FILE), manifest)
    _ok(f"Transfer count: {entry['transfer_count']}  Holder: {entry['current_holder']}")


# ── Stage 4: Authentic verify ─────────────────────────────────────────────────

def stage_verify_authentic(fullscreen, led, mode):
    _banner("STAGE 4 \u2014 Pi terminal: verify AUTHENTIC copy")

    from raspberry_pi.pi_verify_terminal import run_once
    report = run_once(
        file_path        = str(PROTECTED_FILE),
        manifest_path    = str(MANIFEST_FILE),
        mode             = mode,
        registry_path    = str(REGISTRY_FILE),
        provenance_path  = str(PROVENANCE_FILE),
        fullscreen       = fullscreen,
        led              = led,
    )
    if report is None:
        _fail("Verification returned None")
        return False

    traversal = " \u2192 ".join(report.get("traversal_path", []))
    _ok(f"Verdict        : {'AUTHENTIC \u2713' if report['authentic'] else 'TAMPERED \u2717'}")
    _ok(f"Traversal path : {traversal or 'N/A'}")
    _ok(f"Provenance     : {'VALID' if report.get('provenance_chain_valid') else 'BROKEN/N/A'}")
    return report["authentic"]


# ── Stage 5: Tamper tests ─────────────────────────────────────────────────────

def stage_tamper_tests(fullscreen, led, mode):
    _banner("STAGE 5 \u2014 Tamper / attack variants")

    import cv2
    import numpy as np

    _TAMPERED.mkdir(parents=True, exist_ok=True)

    base = cv2.imread(str(PROTECTED_FILE), cv2.IMREAD_GRAYSCALE)
    if base is None:
        _fail(f"Cannot read {PROTECTED_FILE}")
        return []
    h, w = base.shape
    _ok(f"Source image for tamper tests: {w}\u00d7{h} px")

    # (a) Painted patch — top-right quadrant to be visible on this image
    patch_path = _TAMPERED / "tampered2_patch.png"
    out = base.copy()
    out[h//4 : h//4 + 80, w*3//4 - 40 : w*3//4 + 40] = 200   # light grey patch on dark area
    cv2.imwrite(str(patch_path), out)
    _ok("tampered2_patch.png  — 80x80 light-grey patch (top-right region)")

    # (b) Text overlay — "LEAKED" stamp across centre
    text_path = _TAMPERED / "tampered2_text.png"
    out = base.copy()
    colour = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
    cv2.putText(colour, "LEAKED",     (w//3, h//2),
                cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255,255,255), 4, cv2.LINE_AA)
    cv2.putText(colour, "COPY #2",    (w//3, h//2 + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 3, cv2.LINE_AA)
    cv2.imwrite(str(text_path), cv2.cvtColor(colour, cv2.COLOR_BGR2GRAY))
    _ok("tampered2_text.png   — 'LEAKED / COPY #2' text overlay at centre")

    # (c) JPEG Q=50 redistribution
    jpeg_path = _TAMPERED / "tampered2_jpeg.png"
    ok_enc, buf = cv2.imencode(".jpg", base, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    if ok_enc:
        degraded = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
        cv2.imwrite(str(jpeg_path), degraded)
        _ok("tampered2_jpeg.png   — JPEG quality=50 round-trip (redistribution)")
    else:
        _warn("JPEG encode failed"); jpeg_path = None

    # (d) Crop redistribution
    margin    = 32
    crop_path = _TAMPERED / "tampered2_crop.png"
    if h > 2*margin and w > 2*margin:
        cropped = base[margin:h-margin, margin:w-margin]
        cv2.imwrite(str(crop_path), cropped)
        _ok(f"tampered2_crop.png   — {margin}px crop each side \u2192 {cropped.shape[1]}\u00d7{cropped.shape[0]}")
    else:
        _warn("Image too small to crop"); crop_path = None

    # ── Verify each ──────────────────────────────────────────────────
    from raspberry_pi.pi_verify_terminal import run_once

    variants = [
        ("tampered2_patch", patch_path, "deliberate edit \u2192 expect TAMPERED"),
        ("tampered2_text",  text_path,  "deliberate edit \u2192 expect TAMPERED"),
        ("tampered2_jpeg",  jpeg_path,  "redistribution \u2192 honest: may PASS"),
        ("tampered2_crop",  crop_path,  "redistribution \u2192 honest: geometry mismatch"),
    ]
    results = []
    for name, vpath, note in variants:
        if vpath is None:
            results.append({"variant": name, "skipped": True}); continue

        _banner(f"STAGE 5 \u2014 Verifying: {name}")
        print(f"  Note: {note}")
        time.sleep(0.2)

        report = run_once(
            file_path       = str(vpath),
            manifest_path   = str(MANIFEST_FILE),
            mode            = mode,
            registry_path   = str(REGISTRY_FILE),
            provenance_path = str(PROVENANCE_FILE),
            fullscreen      = fullscreen,
            led             = led,
        )
        if report is None:
            results.append({"variant": name, "error": True}); continue

        authentic     = report["authentic"]
        tr            = report.get("tamper_localization", {})
        blocks        = tr.get("block_labels", [])
        supported     = tr.get("supported", False)

        results.append({
            "variant"   : name,
            "authentic" : authentic,
            "verdict"   : "AUTHENTIC" if authentic else "SUSPICIOUS / TAMPERED",
            "led_colour": "GREEN" if authentic else "RED",
            "blocks"    : blocks[:6],
            "supported" : supported,
            "issues"    : report.get("issues", []),
        })

        led_sym  = "\U0001f7e2" if authentic else "\U0001f534"
        blk_str  = ", ".join(blocks[:6]) if blocks else ("N/A" if not supported else "NONE")
        print(f"\n  {led_sym} LED  |  Verdict: {'AUTHENTIC' if authentic else 'SUSPICIOUS / TAMPERED'}")
        print(f"     Tamper blocks : {blk_str}")
        for iss in report.get("issues", []):
            print(f"     Issue         : {iss}")

    return results


# ── Summary ───────────────────────────────────────────────────────────────────

def _summary(authentic_ok, tamper_results):
    _banner("RUN_INPUT1 COMPLETE \u2014 Summary")
    w1, w2, w4 = 22, 26, 36
    print(f"  {'Variant':<{w1}} {'Verdict':<{w2}} {'LED / Blocks'}")
    print("  " + _S*(w1+w2+w4))

    led_str = "GREEN \u2713" if authentic_ok else "RED \u2717"
    print(f"  {'authentic copy (input1)':<{w1}} {'AUTHENTIC' if authentic_ok else 'TAMPERED (?)':<{w2}} {led_str}")

    for r in tamper_results:
        name = r["variant"]
        if r.get("skipped"): print(f"  {name:<{w1}} {'skipped':<{w2}}"); continue
        if r.get("error"):   print(f"  {name:<{w1}} {'ERROR':<{w2}}"); continue
        blocks  = r["blocks"]
        blk_str = ", ".join(blocks) if blocks else ("geometry mismatch" if not r["supported"] else "none")
        print(f"  {name:<{w1}} {r['verdict']:<{w2}} {r['led_colour']}  |  {blk_str}")

    print("  " + _S*(w1+w2+w4))
    print(f"\n  Image: samples/input1.jpg  (1280\u00d7720, hand-raised photo)")
    print(f"  Document ID : {DOC_ID}")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=f"Full pipeline on samples/input1.jpg  ({DOC_ID})"
    )
    parser.add_argument("--no-led",      action="store_true")
    parser.add_argument("--fullscreen",  action="store_true")
    parser.add_argument("--skip-issue",  action="store_true",
                        help="Skip stages 1-3 (files already generated)")
    parser.add_argument("--skip-tamper", action="store_true")
    parser.add_argument("--mode", default="online", choices=["offline", "online"])
    args = parser.parse_args()

    from raspberry_pi.gpio_led import LedIndicator
    led = None if args.no_led else LedIndicator()

    authentic_ok   = False
    tamper_results = []

    try:
        if not args.skip_issue:
            stage_issue()
            stage_transfer("Abhishek", "Rahul")
            stage_transfer("Rahul",    "Priya")
        else:
            missing = [p for p in (PROTECTED_FILE, MANIFEST_FILE) if not p.exists()]
            if missing:
                for p in missing: _fail(f"Missing: {p}")
                _fail("Run without --skip-issue first.")
                sys.exit(1)
            _ok("Skipping issue/transfer stages (files already present).")

        authentic_ok = stage_verify_authentic(args.fullscreen, led, args.mode)

        if not args.skip_tamper:
            tamper_results = stage_tamper_tests(args.fullscreen, led, args.mode)

    finally:
        if led is not None:
            led.cleanup()

    _summary(authentic_ok, tamper_results)
    sys.exit(0 if authentic_ok else 1)


if __name__ == "__main__":
    main()
