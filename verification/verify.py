import datetime
import json
from pathlib import Path

from Crypto.PublicKey import RSA

from provenance.chain import get_document as get_provenance, traversal_path, verify_chain_integrity
from utils.forensics import parse_watermark_text
from utils.hash import generate_hash, signature_from_text, verify_signature
from verification.tamper_localization import localize_tamper
from watermark.extract import extract_watermark_details


def _load_json(path):
    with open(path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def verify_document(file_path, manifest_path, mode="offline", registry_path=None, provenance_path=None):
    manifest = _load_json(manifest_path)
    public_key = RSA.import_key(manifest["public_key_pem"])
    signature = signature_from_text(manifest["signature_b64"])

    current_hash = generate_hash(file_path)
    hash_ok = current_hash == manifest["protected_hash"]
    signature_ok = verify_signature(file_path, signature, public_key)

    expected_shape = tuple(manifest.get("image_shape", [])) if manifest.get("image_shape") else None
    watermark_details = extract_watermark_details(
        file_path,
        expected_shape=expected_shape,
        thumbnail_b64=manifest.get("reference_thumbnail_b64"),
    )
    extracted_text = watermark_details["watermark"] if watermark_details["valid"] else None
    watermark_fields = parse_watermark_text(extracted_text) if extracted_text else {}
    watermark_ok = extracted_text == manifest["watermark_text"]

    registry_ok = None
    if mode == "online":
        registry_ok = False
        if registry_path and Path(registry_path).exists():
            registry = _load_json(registry_path)
            entry = registry.get(manifest["document_id"])
            registry_ok = bool(
                entry
                and entry.get("protected_hash") == manifest["protected_hash"]
                and entry.get("issuer_id") == manifest["issuer_id"]
            )

    # Block-level tamper localization (works off the manifest's baseline
    # block fingerprints, independent of hash/signature/watermark checks).
    tamper_report = localize_tamper(file_path, manifest)

    # Provenance / traversal lookup (optional — only if a provenance file
    # was supplied, e.g. by the Raspberry Pi terminal or a verify --provenance flag).
    provenance_entry = None
    provenance_chain_ok = None
    if provenance_path and Path(provenance_path).exists():
        provenance_entry = get_provenance(provenance_path, manifest["document_id"])
        if provenance_entry:
            provenance_chain_ok = verify_chain_integrity(provenance_path, manifest["document_id"])["valid"]

    issues = []
    if not hash_ok:
        issues.append("Protected hash mismatch")
    if not signature_ok:
        issues.append("Digital signature invalid")
    if not watermark_ok:
        issues.append("Watermark missing or altered")
    if mode == "online" and not registry_ok:
        issues.append("Online registry lookup failed")
    if tamper_report.get("supported") and tamper_report.get("tampered"):
        issues.append(
            f"Tamper localized in {len(tamper_report['blocks'])} block(s): "
            + ", ".join(tamper_report["block_labels"][:10])
        )
    if provenance_chain_ok is False:
        issues.append("Provenance chain integrity check failed")

    authentic = (
        hash_ok
        and signature_ok
        and watermark_ok
        and (registry_ok is not False)
        and not (tamper_report.get("supported") and tamper_report.get("tampered"))
        and (provenance_chain_ok is not False)
    )
    report = {
        "mode": mode,
        "checked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_path": file_path,
        "document_id": manifest["document_id"],
        "hash_valid": hash_ok,
        "signature_valid": signature_ok,
        "watermark_valid": watermark_ok,
        "watermark_text": extracted_text,
        "watermark_confidence": watermark_details.get("confidence", 0.0),
        "issuer_identity": watermark_fields.get("Issuer"),
        "sender_identity": watermark_fields.get("Sender"),
        "receiver_identity": watermark_fields.get("Receiver") or watermark_fields.get("User"),
        "version": watermark_fields.get("Version"),
        "registry_valid": registry_ok,
        "tamper_localization": tamper_report,
        "provenance": provenance_entry,
        "provenance_chain_valid": provenance_chain_ok,
        "traversal_path": traversal_path(provenance_path, manifest["document_id"]) if provenance_entry else [],
        "authentic": authentic,
        "issues": issues,
    }

    print("\n" + "=" * 58)
    print(f"DOCUMENT VERIFICATION REPORT ({mode.upper()} MODE)")
    print("=" * 58)
    print(f"File              : {report['file_path']}")
    print(f"Document ID       : {report['document_id']}")
    print(f"Checked At        : {report['checked_at']}")
    print(f"Hash Check        : {'PASS' if hash_ok else 'FAIL'}")
    print(f"Signature Check   : {'PASS' if signature_ok else 'FAIL'}")
    print(f"Watermark Check   : {'PASS' if watermark_ok else 'FAIL'}")
    print(f"Watermark Text    : {extracted_text or 'Not recovered'}")
    print(f"Watermark Score   : {report['watermark_confidence']}")
    print(f"Current Holder    : {report['receiver_identity'] or 'Unknown'}")
    print(f"Copy Version      : {report['version'] or 'Unknown'}")
    if mode == "online":
        print(f"Registry Check    : {'PASS' if registry_ok else 'FAIL'}")
    if tamper_report.get("supported"):
        loc = "None" if not tamper_report["tampered"] else ", ".join(tamper_report["block_labels"][:10])
        print(f"Tamper Localization: {loc} ({tamper_report['percent_tampered']}% of blocks)")
    if provenance_entry is not None:
        print(f"Provenance Chain  : {'VALID' if provenance_chain_ok else 'BROKEN'}")
        print(f"Traversal Path    : {' -> '.join(report['traversal_path'])}")
    print(f"Verdict           : {'AUTHENTIC' if authentic else 'SUSPICIOUS / TAMPERED'}")
    if issues:
        print("Issues            : " + "; ".join(issues))
    print("=" * 58 + "\n")

    return report
