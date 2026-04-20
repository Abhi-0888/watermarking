import argparse
import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

import cv2

from encryption.aes import decrypt_file, encrypt_file, generate_key
from encryption.rsa import decrypt_key, encrypt_key, generate_keys
from utils.forensics import generate_forensic_report
from utils.metrics import (
    measure_embedding_capacity,
    measure_encryption_time,
    measure_extraction_accuracy,
    measure_false_positive_rate,
    measure_psnr,
    print_metrics,
)
from verification.attacks import create_attack_set
from verification.package import build_manifest, update_registry, write_manifest
from verification.verify import verify_document
from watermark.embed import embed_watermark
from watermark.extract import extract_watermark_details


BASE_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = BASE_DIR / "samples"
INPUT_FILE = SAMPLES_DIR / "input.png"
ENCRYPTED_FILE = SAMPLES_DIR / "encrypted.bin"
DECRYPTED_FILE = SAMPLES_DIR / "decrypted.png"
PROTECTED_FILE = SAMPLES_DIR / "watermarked.png"
MANIFEST_FILE = SAMPLES_DIR / "manifest.json"
REGISTRY_FILE = SAMPLES_DIR / "registry.json"
ATTACK_DIR = SAMPLES_DIR / "attacks"


def create_watermark_text(issuer_id, receiver_identity, document_id, timestamp):
    return f"ISS:{issuer_id}|RCV:{receiver_identity}|DOC:{document_id}|TS:{timestamp}"


def evaluate_attack_file(attack_name, attack_file, expected_shape, watermark_text=None, thumbnail_b64=None):
    details = extract_watermark_details(
        attack_file,
        expected_shape=expected_shape,
        fast_mode=True,
        thumbnail_b64=thumbnail_b64,
    )
    extracted_text = details["watermark"] if details["valid"] else ""
    result = {
        "attack": attack_name,
        "file": attack_file,
        "valid": details["valid"],
        "confidence": details.get("confidence", 0.0),
    }
    if watermark_text is not None:
        result["accuracy"] = measure_extraction_accuracy(watermark_text, extracted_text)
    return result


def run_attack_evaluation(protected_file, input_file, expected_shape, watermark_text, thumbnail_b64=None):
    print("Phase 6: Attack simulation")
    attacks = create_attack_set(str(protected_file), str(ATTACK_DIR))
    attack_results = {}
    max_workers = min(4, max(1, (os.cpu_count() or 2) - 1))
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                evaluate_attack_file,
                attack_name,
                attack_file,
                expected_shape,
                watermark_text,
                thumbnail_b64,
            ): attack_name
            for attack_name, attack_file in attacks.items()
        }
        for future in as_completed(futures):
            result = future.result()
            attack_name = result["attack"]
            attack_results[attack_name] = {
                "file": result["file"],
                "valid": result["valid"],
                "confidence": result["confidence"],
                "accuracy": result["accuracy"],
            }
            print(
                f"  {attack_name:<12} valid={result['valid']} "
                f"confidence={result['confidence']} accuracy={result['accuracy']}"
            )

    clean_results = []
    clean_attacks = create_attack_set(str(input_file), str(ATTACK_DIR / "clean"))
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                evaluate_attack_file,
                attack_name,
                attack_file,
                expected_shape,
                None,
                thumbnail_b64,
            ): attack_name
            for attack_name, attack_file in clean_attacks.items()
        }
        for future in as_completed(futures):
            result = future.result()
            clean_results.append({"attack": result["attack"], "valid": result["valid"]})

    attack_pass_rate = round(
        sum(1 for item in attack_results.values() if item["valid"]) / len(attack_results),
        4,
    )
    false_positive_rate = measure_false_positive_rate(clean_results)
    return attack_results, attack_pass_rate, false_positive_rate


def protect_document(run_full_evaluation=False, present_mode=False):
    issuer_id = "CollegeXYZ"
    receiver_identity = "Abhishek"
    document_id = "DOC-2026-001"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    watermark_text = create_watermark_text(issuer_id, receiver_identity, document_id, timestamp)

    print("\nSECURE DOCUMENT SYSTEM STARTING\n")
    print("Phase 1: Hybrid encryption")
    aes_key = generate_key()
    private_key, public_key = generate_keys()
    encrypted_aes_key = encrypt_key(aes_key, public_key)
    decrypted_aes_key = decrypt_key(encrypted_aes_key, private_key)

    _, encryption_ms = measure_encryption_time(encrypt_file, str(INPUT_FILE), str(ENCRYPTED_FILE), decrypted_aes_key)
    decrypt_file(str(ENCRYPTED_FILE), str(DECRYPTED_FILE), decrypted_aes_key)
    print(f"  Encrypted file written to {ENCRYPTED_FILE}")
    print(f"  Decrypted reference written to {DECRYPTED_FILE}")

    print("\nPhase 2: Invisible watermarking")
    embed_info = embed_watermark(str(DECRYPTED_FILE), str(PROTECTED_FILE), watermark_text)
    print(f"  Protected file written to {PROTECTED_FILE}")
    print(f"  Packet redundancy: {embed_info['redundancy']}x")

    print("\nPhase 3: Signature and manifest packaging")
    manifest = build_manifest(
        original_file=str(INPUT_FILE),
        protected_file=str(PROTECTED_FILE),
        watermark_text=watermark_text,
        private_key=private_key,
        public_key=public_key,
        issuer_id=issuer_id,
        receiver_identity=receiver_identity,
        document_id=document_id,
        timestamp=timestamp,
        encrypted_aes_key=encrypted_aes_key,
        image_shape=cv2.imread(str(DECRYPTED_FILE), cv2.IMREAD_GRAYSCALE).shape,
    )
    write_manifest(str(MANIFEST_FILE), manifest)
    update_registry(str(REGISTRY_FILE), manifest)
    print(f"  Manifest written to {MANIFEST_FILE}")
    print(f"  Online registry updated at {REGISTRY_FILE}")

    print("\nPhase 4: Verification")
    offline_report = verify_document(str(PROTECTED_FILE), str(MANIFEST_FILE), mode="offline")
    if run_full_evaluation:
        online_report = verify_document(
            str(PROTECTED_FILE),
            str(MANIFEST_FILE),
            mode="online",
            registry_path=str(REGISTRY_FILE),
        )
    elif present_mode:
        online_report = None
        print("  Online verification skipped in presentation mode.")
    else:
        online_report = None
        print("  Online verification skipped in quick demo mode.")

    if present_mode:
        print("Phase 5: Leak traceability")
        print(f"  Recipient traced : {offline_report['receiver_identity'] or 'Unknown'}")
        print(f"  Document ID      : {offline_report['document_id']}")
        forensic_report = {
            "suspected_recipient": offline_report["receiver_identity"],
            "document_id": offline_report["document_id"],
            "watermark_text": offline_report["watermark_text"],
        }
    else:
        print("Phase 5: Leak traceability")
        forensic_report = generate_forensic_report(offline_report["watermark_text"] or "", str(PROTECTED_FILE))

    attack_results = {}
    attack_pass_rate = None
    false_positive_rate = None
    if run_full_evaluation:
        attack_results, attack_pass_rate, false_positive_rate = run_attack_evaluation(
            PROTECTED_FILE,
            INPUT_FILE,
            manifest["image_shape"],
            watermark_text,
            manifest.get("reference_thumbnail_b64"),
        )
    else:
        print("Phase 6: Attack simulation")
        if present_mode:
            print("  Skipped in presentation mode. Run `python main.py full` for full robustness evaluation.")
        else:
            print("  Skipped in quick demo mode. Run `python main.py full` for full robustness evaluation.")

    print("\nPhase 7: Metrics")
    capacity = measure_embedding_capacity(str(DECRYPTED_FILE))
    metrics_summary = {
        "psnr": measure_psnr(str(DECRYPTED_FILE), str(PROTECTED_FILE)),
        "encryption_ms": encryption_ms,
        "capacity_chars": capacity["usable_chars"],
        "packet_bits": capacity["packet_bits"],
        "extraction_accuracy": (
            "Verified in presentation mode"
            if present_mode
            else "Verified in quick demo mode"
        ) if not run_full_evaluation else measure_extraction_accuracy(
            watermark_text,
            (extract_watermark_details(str(PROTECTED_FILE), expected_shape=manifest["image_shape"])["watermark"] or ""),
        ),
        "false_positive_rate": false_positive_rate if false_positive_rate is not None else (
            "Skipped in presentation mode" if present_mode else "Skipped in quick demo mode"
        ),
        "attack_pass_rate": attack_pass_rate if attack_pass_rate is not None else (
            "Skipped in presentation mode" if present_mode else "Skipped in quick demo mode"
        ),
    }
    print_metrics(metrics_summary)

    return {
        "manifest_path": str(MANIFEST_FILE),
        "registry_path": str(REGISTRY_FILE),
        "protected_file": str(PROTECTED_FILE),
        "offline_report": offline_report,
        "online_report": online_report,
        "forensic_report": forensic_report,
        "attack_results": attack_results,
        "metrics": metrics_summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Secure Digital Document Protection System")
    parser.add_argument(
        "command",
        nargs="?",
        default="demo",
        choices=["present", "demo", "full", "verify"],
        help="Run the presentation demo, quick demo, full evaluation, or verify an existing protected file.",
    )
    parser.add_argument("--file", dest="file_path", help="Protected file path for verification")
    parser.add_argument("--manifest", dest="manifest_path", help="Manifest path for verification")
    parser.add_argument(
        "--mode",
        default="offline",
        choices=["offline", "online"],
        help="Verification mode",
    )
    parser.add_argument("--registry", dest="registry_path", help="Registry file for online verification")
    args = parser.parse_args()

    if args.command == "verify":
        if not args.file_path or not args.manifest_path:
            raise SystemExit("verify requires --file and --manifest")
        verify_document(args.file_path, args.manifest_path, mode=args.mode, registry_path=args.registry_path)
        return

    protect_document(
        run_full_evaluation=(args.command == "full"),
        present_mode=(args.command == "present"),
    )


if __name__ == "__main__":
    main()
