"""
Authorized document transfer.

Moves a protected document from its current holder to a new receiver:

  1. Re-embeds the watermark with an updated payload
     (ISS unchanged, SRC = current holder, RCV = new receiver, VER += 1).
  2. Re-hashes and re-signs the new copy with the issuer's persisted key.
  3. Recomputes the block-level tamper-localization baseline for the new copy.
  4. Appends a hash-linked record to the provenance/traversal chain.
  5. Updates the online registry's current holder / transfer count.

Usage:
    python transfer.py --doc-id DOC-2026-001 --from Abhishek --to Rahul
    python transfer.py --doc-id DOC-2026-001 --from Rahul --to Priya
"""

import argparse
import datetime
import shutil
from pathlib import Path

import cv2

from encryption.rsa import load_keys
from main import create_watermark_text
from provenance.chain import add_transfer, get_document as get_provenance_document
from utils.hash import generate_hash, sign_document, signature_to_text
from verification.package import update_registry, write_manifest
from verification.tamper_localization import attach_block_descriptors
from watermark.embed import embed_watermark

BASE_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = BASE_DIR / "samples"
MANIFEST_FILE = SAMPLES_DIR / "manifest.json"
REGISTRY_FILE = SAMPLES_DIR / "registry.json"
PROVENANCE_FILE = SAMPLES_DIR / "provenance.json"
KEY_DIR = SAMPLES_DIR / "keys"
CURRENT_PROTECTED_FILE = SAMPLES_DIR / "watermarked.png"


def _load_json(path):
    import json

    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def transfer_document(document_id, sender, receiver, manifest_path=str(MANIFEST_FILE),
                       protected_file=str(CURRENT_PROTECTED_FILE), registry_path=str(REGISTRY_FILE),
                       provenance_path=str(PROVENANCE_FILE), key_dir=str(KEY_DIR)):
    manifest = _load_json(manifest_path)
    if manifest["document_id"] != document_id:
        raise ValueError(
            f"Manifest at {manifest_path} is for {manifest['document_id']}, not {document_id}"
        )
    if manifest.get("receiver_identity") != sender and manifest.get("sender_identity") != sender:
        print(
            f"  Warning: manifest's current holder is "
            f"'{manifest.get('receiver_identity')}', not '{sender}'. Proceeding anyway."
        )

    private_key, public_key = load_keys(key_dir)

    new_version = manifest.get("version", 1) + 1
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    watermark_text = create_watermark_text(
        manifest["issuer_id"], sender, receiver, document_id, new_version, timestamp
    )

    print(f"\nTRANSFER: {sender} -> {receiver}  (v{manifest.get('version', 1)} -> v{new_version})\n")

    print("Step 1: Re-embed watermark for the new holder")
    versioned_path = SAMPLES_DIR / f"watermarked_v{new_version}.png"
    embed_watermark(protected_file, str(versioned_path), watermark_text)
    shutil.copyfile(versioned_path, protected_file)  # "current" pointer
    print(f"  New copy written to {versioned_path} (also updated {protected_file})")

    print("Step 2: Re-hash and re-sign")
    signature = sign_document(protected_file, private_key)
    protected_hash = generate_hash(protected_file)

    print("Step 3: Recompute tamper-localization baseline")
    manifest["watermark_text"] = watermark_text
    manifest["protected_hash"] = protected_hash
    manifest["signature_b64"] = signature_to_text(signature)
    manifest["sender_identity"] = sender
    manifest["receiver_identity"] = receiver
    manifest["version"] = new_version
    manifest["timestamp"] = timestamp
    manifest["image_shape"] = list(cv2.imread(protected_file, cv2.IMREAD_GRAYSCALE).shape)
    attach_block_descriptors(manifest, protected_file)

    versioned_manifest_path = SAMPLES_DIR / f"manifest_v{new_version}.json"
    write_manifest(str(versioned_manifest_path), manifest)
    write_manifest(manifest_path, manifest)  # "current" pointer
    print(f"  Manifest written to {versioned_manifest_path} (also updated {manifest_path})")

    print("Step 4: Append hash-linked provenance record")
    if get_provenance_document(provenance_path, document_id) is None:
        raise RuntimeError(
            f"No provenance genesis record for {document_id}. "
            "Run `python main.py demo` (or `present`/`full`) first to issue the document."
        )
    entry = add_transfer(
        provenance_path,
        document_id=document_id,
        sender=sender,
        receiver=receiver,
        version=new_version,
        protected_hash=protected_hash,
        timestamp=timestamp,
    )
    print(f"  Transfer count: {entry['transfer_count']}   Current holder: {entry['current_holder']}")

    print("Step 5: Update online registry")
    update_registry(registry_path, manifest)
    print(f"  Registry updated at {registry_path}")

    print(f"\nTransfer complete: {sender} -> {receiver} (copy v{new_version})\n")
    return {
        "manifest": manifest,
        "protected_file": str(versioned_path),
        "provenance_entry": entry,
    }


def main():
    parser = argparse.ArgumentParser(description="Authorize a document transfer")
    parser.add_argument("--doc-id", required=True)
    parser.add_argument("--from", dest="sender", required=True)
    parser.add_argument("--to", dest="receiver", required=True)
    parser.add_argument("--manifest", default=str(MANIFEST_FILE))
    parser.add_argument("--file", dest="protected_file", default=str(CURRENT_PROTECTED_FILE))
    parser.add_argument("--registry", default=str(REGISTRY_FILE))
    parser.add_argument("--provenance", default=str(PROVENANCE_FILE))
    parser.add_argument("--key-dir", default=str(KEY_DIR))
    args = parser.parse_args()

    transfer_document(
        document_id=args.doc_id,
        sender=args.sender,
        receiver=args.receiver,
        manifest_path=args.manifest,
        protected_file=args.protected_file,
        registry_path=args.registry,
        provenance_path=args.provenance,
        key_dir=args.key_dir,
    )


if __name__ == "__main__":
    main()
