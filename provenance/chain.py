"""
Provenance / traversal layer.

Every authorized transfer of a protected document is appended as a record
to a per-document chain:

    H1 -> H2 -> H3 -> H4

Each record stores the hash of the previous record, so the traversal
history becomes tamper-evident (any edit to an earlier record changes its
hash, which breaks every hash that follows it) without needing a
blockchain: a single append-only JSON file plus hash chaining is enough
for this project's threat model (a single trusted registry, not a
distributed/multi-party ledger).
"""

import datetime
import hashlib
import json
from pathlib import Path

GENESIS_HASH = "0" * 64


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load(path):
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def _canonical(record):
    # Sorted keys + compact separators so the same logical record always
    # hashes to the same value regardless of dict insertion order.
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def compute_record_hash(record, prev_hash):
    """record_hash = SHA256(prev_hash || canonical_json(record_without_hash))"""
    payload = (prev_hash + _canonical(record)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def init_document(provenance_path, document_id, issuer_id, initial_holder, protected_hash,
                   version=1, timestamp=None):
    """Create the genesis record for a document: issuer -> initial holder."""
    chain = _load(provenance_path)
    if document_id in chain:
        return chain[document_id]

    record_core = {
        "seq": 1,
        "from": issuer_id,
        "to": initial_holder,
        "version": version,
        "protected_hash": protected_hash,
        "timestamp": timestamp or _now(),
    }
    record_hash = compute_record_hash(record_core, GENESIS_HASH)
    record = {**record_core, "prev_hash": GENESIS_HASH, "record_hash": record_hash}

    chain[document_id] = {
        "document_id": document_id,
        "original_issuer": issuer_id,
        "current_holder": initial_holder,
        "transfer_count": 1,
        "current_version": version,
        "history": [record],
    }
    _save(provenance_path, chain)
    return chain[document_id]


def add_transfer(provenance_path, document_id, sender, receiver, version, protected_hash,
                  timestamp=None):
    """Append a new authorized transfer, linked to the previous record's hash."""
    chain = _load(provenance_path)
    if document_id not in chain:
        raise ValueError(f"No provenance entry for {document_id}; call init_document first.")

    entry = chain[document_id]
    history = entry["history"]
    prev_hash = history[-1]["record_hash"] if history else GENESIS_HASH

    record_core = {
        "seq": len(history) + 1,
        "from": sender,
        "to": receiver,
        "version": version,
        "protected_hash": protected_hash,
        "timestamp": timestamp or _now(),
    }
    record_hash = compute_record_hash(record_core, prev_hash)
    record = {**record_core, "prev_hash": prev_hash, "record_hash": record_hash}

    history.append(record)
    entry["current_holder"] = receiver
    entry["transfer_count"] = len(history)
    entry["current_version"] = version

    _save(provenance_path, chain)
    return entry


def get_document(provenance_path, document_id):
    chain = _load(provenance_path)
    return chain.get(document_id)


def verify_chain_integrity(provenance_path, document_id):
    """
    Recompute every hash in the chain from scratch and confirm the links
    match. Returns a report dict; `valid` is False and `broken_at` is set
    to the first sequence number where the recorded hash no longer matches
    the recomputed hash (i.e. the record, or an earlier one, was edited).
    """
    entry = get_document(provenance_path, document_id)
    if entry is None:
        return {"valid": False, "reason": "document_not_found", "broken_at": None}

    prev_hash = GENESIS_HASH
    for record in entry["history"]:
        record_core = {
            "seq": record["seq"],
            "from": record["from"],
            "to": record["to"],
            "version": record["version"],
            "protected_hash": record["protected_hash"],
            "timestamp": record["timestamp"],
        }
        if record["prev_hash"] != prev_hash:
            return {"valid": False, "reason": "broken_link", "broken_at": record["seq"]}
        expected_hash = compute_record_hash(record_core, prev_hash)
        if expected_hash != record["record_hash"]:
            return {"valid": False, "reason": "record_modified", "broken_at": record["seq"]}
        prev_hash = record["record_hash"]

    return {"valid": True, "reason": None, "broken_at": None}


def traversal_path(provenance_path, document_id):
    """Human-readable 'College -> Abhishek -> Rahul -> Priya' style path."""
    entry = get_document(provenance_path, document_id)
    if entry is None:
        return []
    if not entry["history"]:
        return [entry["original_issuer"]]
    path = [entry["history"][0]["from"]]
    path.extend(record["to"] for record in entry["history"])
    return path
