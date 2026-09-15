# Presentation Guide

Slide-by-slide talking points for the Secure Digital Document Protection System demo.

---

## Slide 1 — Title

**Secure Digital Document Protection System**

> "This project protects digital documents using encryption, invisible watermarking, tamper detection, provenance tracking, and forensic traceability."

---

## Slide 2 — Problem

Digital documents can be:

- leaked
- tampered with
- redistributed without authorization
- difficult to verify offline

**Goal:** Build a system that can protect, verify, trace, and localize tampering in digital documents.

---

## Slide 3 — Objectives

- Ensure confidentiality (AES + RSA)
- Ensure authenticity (hash + digital signature)
- Detect tampering (hash/signature + block-level localization)
- Track authorized transfers (hash-linked provenance chain)
- Identify leaked recipient copies (watermark forensics)
- Support offline, online, desktop, web, and Raspberry Pi verification

---

## Slide 4 — Technologies

| Layer | Technology |
|-------|------------|
| Language | Python |
| Image processing | OpenCV, NumPy |
| Encryption | AES-256, RSA-2048 |
| Integrity | SHA-256, PKCS#1 v1.5 signatures |
| Watermarking | DCT-domain invisible embedding |
| Hardware | Raspberry Pi + GPIO LEDs (optional) |

---

## Slide 5 — Architecture

```
Input → AES encrypt → RSA key wrap → Decrypt reference
      → Watermark embed → Hash + Sign → Manifest + Registry + Provenance
      → Verify → Forensic trace → Attack evaluation
```

On transfer: re-watermark → re-sign → re-baseline tamper grid → append provenance.

---

## Slide 6 — Cryptographic Layer

- **AES** encrypts the file content
- **RSA** protects the AES key
- **SHA-256** creates a file fingerprint
- **Digital signature** proves the document is genuine

> "AES protects the content, RSA protects the key, and the signature proves the document is genuine."

Demo: `py -3 main.py present`

---

## Slide 7 — Watermarking Layer

- Invisible watermark embedded in DCT coefficients
- Payload: issuer, sender, receiver, document ID, version, timestamp
- Repeated across image blocks for redundancy (5×+)

> "Even if the file is redistributed, the hidden identity of the recipient can be recovered from the watermarked copy."

Show extracted watermark from verification report.

---

## Slide 8 — Verification

**Offline:** manifest hash + signature + watermark  
**Online:** above + registry lookup  
**Tamper localization:** 16×16 block fingerprint comparison  
**Provenance:** hash-linked transfer chain integrity

| Interface | Command |
|-----------|---------|
| CLI | `py -3 main.py verify …` |
| Desktop | `py -3 gui_verify.py` |
| Web | `py -3 web_verify.py` |
| Raspberry Pi | `py -3 raspberry_pi/pi_verify_terminal.py …` |

---

## Slide 9 — Document Transfer & Provenance

Authorized transfer flow:

```
CollegeXYZ → Abhishek → Rahul → Priya
```

Each transfer:

1. Re-embeds watermark (SRC/RCV/VER updated)
2. Re-signs with persisted issuer key
3. Appends hash-linked provenance record
4. Updates online registry

Demo:

```bash
py -3 transfer.py --doc-id DOC-2026-001 --from Abhishek --to Rahul
py -3 main.py verify … --provenance samples/provenance.json
```

> "Every authorized handoff is recorded in a tamper-evident chain — any edit to history breaks the links."

---

## Slide 10 — Tamper Localization

Beyond "was it tampered?" → "where was it tampered?"

- Image split into 16×16 blocks at protect/transfer time
- Per-block perceptual fingerprints stored in manifest
- At verify time, drifted blocks flagged (e.g. `B6-9, B7-10`)

Demo: show verification report with localized blocks on a synthetically edited copy.

---

## Slide 11 — Leak Traceability

- Extract watermark from leaked copy
- Identify recipient, sender, document ID, version
- Generate forensic report

> "If a protected copy leaks, the system can identify the intended recipient of that copy."

---

## Slide 12 — Raspberry Pi Terminal

- Verification kiosk with HDMI dashboard
- Green LED = authentic, Red LED = tampered
- Shows traversal path, holder, version, tamper blocks
- Pi holds **public key only** — private key stays on issuer machine

Mock mode on laptop: `[mock LED] GREEN/RED` printed to console.

---

## Slide 13 — Attack Simulation

Attacks tested (`py -3 main.py full`):

| Attack | Result |
|--------|--------|
| Compression | PASS |
| Cropping | PASS |
| Scaling | PASS |
| Screenshot simulation | PASS |
| Minor edit | PASS |

Metrics: PSNR ~21.8 dB, extraction accuracy 1.0, attack pass rate 1.0.

Runtime: present ~5 s, full ~40 s.

---

## Slide 14 — Limitations

> "The system survives compression, cropping, scaling, screenshot-style redistribution, and minor edits in our evaluation. Advanced real-world camera-display capture remains future work. The Pi terminal verifies documents but is not a hardware security module."

Be explicit: no TPM/HSM — scope is appropriate for a BTech prototype.

---

## Slide 15 — Future Scope

- DWT + DCT hybrid embedding
- Error-correcting codes
- Synchronization markers
- Stronger screenshot recovery
- Enhanced web upload interface

---

## Slide 16 — Conclusion

> "The project combines security, verification, traceability, transfer provenance, and tamper localization into one system — a practical prototype for secure digital document protection with end-to-end verification across desktop, web, and Raspberry Pi."

---

## Demo Script (recommended order)

1. `py -3 main.py present` — fast pipeline overview
2. `py -3 main.py verify … --provenance …` — show verification report
3. `py -3 transfer.py --from Abhishek --to Rahul` — live transfer
4. `py -3 main.py verify …` — show updated holder + traversal path
5. `py -3 gui_verify.py` or `py -3 web_verify.py` — upload interface
6. `py -3 raspberry_pi/pi_verify_terminal.py …` — Pi terminal (mock LEDs)
7. (Optional) `py -3 main.py full` — full attack results if time permits
