# Secure Digital Document Protection System

## 1. Problem Statement

The goal of this project is to build a secure digital document protection system that combines:

- public key cryptography
- symmetric encryption
- invisible watermarking
- tamper detection

The system is designed to support:

- document authenticity
- leak traceability
- resistance against common redistribution attacks
- offline and online-style verification

## 2. System Overview

This project protects a digital document in multiple layers:

1. The original document is encrypted using AES.
2. The AES key is protected using RSA.
3. A personalized invisible watermark is embedded into the delivered copy.
4. The final protected copy is hashed and digitally signed.
5. A manifest is generated for offline verification.
6. A registry entry is generated for simulated online verification.
7. If a leaked copy is found, the watermark is extracted and used for forensic traceability.

## 3. Modules

### 3.1 Cryptographic Layer

- AES encryption and decryption
- RSA key-pair generation
- RSA protection of AES key
- SHA-256 hashing
- digital signature creation and verification

Files:

- `encryption/aes.py`
- `encryption/rsa.py`
- `utils/hash.py`

### 3.2 Watermarking Layer

- embeds an invisible structured watermark
- uses DCT-domain coefficient relationships
- stores issuer, receiver, document ID, and timestamp
- repeats the watermark packet across many image blocks for redundancy

Files:

- `watermark/embed.py`
- `watermark/extract.py`

### 3.3 Verification Layer

- verifies protected hash
- verifies digital signature
- verifies extracted watermark
- supports offline manifest-based verification
- supports simulated online registry-based verification
- includes a desktop upload-style verification interface

Files:

- `verification/verify.py`
- `verification/package.py`
- `gui_verify.py`

### 3.4 Attack Simulation and Evaluation

- compression attack
- cropping attack
- scaling attack
- screenshot simulation
- minor edit simulation

Files:

- `verification/attacks.py`
- `utils/metrics.py`

### 3.5 Leak Traceability

- extracts watermark from leaked copy
- identifies recipient and document metadata
- generates forensic leak report

Files:

- `utils/forensics.py`

## 4. Watermark Format

The watermark stores:

- `ISS` = issuer ID
- `RCV` = receiver identity
- `DOC` = document ID
- `TS` = timestamp

Example:

```text
ISS:CollegeXYZ|RCV:Abhishek|DOC:DOC-2026-001|TS:2026-04-07 23:48:03
```

## 5. Working Flow

1. Load original input image.
2. Generate AES key.
3. Generate RSA public/private keys.
4. Encrypt document with AES.
5. Encrypt AES key with RSA public key.
6. Decrypt AES key with RSA private key for recovery check.
7. Produce decrypted reference image.
8. Embed invisible personalized watermark into the protected copy.
9. Hash the final protected file.
10. Digitally sign the final protected file.
11. Write a manifest for offline verification.
12. Write a registry entry for online-style verification.
13. Verify authenticity in offline mode.
14. Verify authenticity in online mode.
15. Extract watermark for forensic reporting.
16. Simulate common attacks and measure robustness when running the full evaluation mode.

## 6. Final Experimental Output

Observed final output from `python main.py full`:

- Offline verification: PASS
- Online verification: PASS
- Leak traceability: PASS
- Compression attack recovery: PASS
- Cropping attack recovery: PASS
- Scaling attack recovery: PASS
- Minor edit recovery: PASS
- Screenshot recovery: PASS

Measured metrics:

- PSNR: `21.76 dB`
- Encryption time: `8.93 ms`
- Embedding capacity: `80 characters`
- Packet size: `736 bits`
- Extraction accuracy: `1.0`
- False positive rate: `0.0`
- Attack pass rate: `1.0`

Execution modes:

- `python main.py present` for a very fast live demo
- `python main.py` for a quick demo flow
- `python main.py full` for all outputs in one run

Current observed runtime:

- `present` mode: about 5 seconds
- `full` mode: about 40 seconds
- `python gui_verify.py` launches the upload-style desktop verifier
- `python web_verify.py` launches the dependency-free web upload verifier

## 7. Requirement Mapping

### Fully Implemented

- AES encryption
- RSA protection of AES key
- digital signature
- SHA-256 hashing
- invisible watermark with issuer, receiver, document ID, and timestamp
- tamper detection using hash and signature
- offline verification
- online-style verification
- desktop upload-style verification interface
- web upload-style verification interface
- forensic leak report
- PSNR measurement
- embedding capacity measurement
- encryption time measurement
- extraction accuracy measurement
- false positive rate measurement

### Implemented and Demonstrated Successfully

- authenticity verification
- leak traceability
- compression resilience
- cropping resilience
- scaling resilience
- screenshot resilience in the current evaluation flow
- resistance to minor edits

The system now demonstrates successful recovery under the implemented screenshot-style redistribution simulation, together with compression, cropping, scaling, and minor edit resilience.

## 8. Strengths of the Project

- correct hybrid cryptography pipeline
- final protected copy is the one being signed and verified
- personalized watermarking for traceability
- low false positive rate
- good extraction accuracy on supported attacks
- modular project design
- clear end-to-end verification workflow
- multiple execution modes for fast presentation and full evaluation
- desktop upload verifier for faculty demonstration
- web upload verifier for browser-based verification

## 9. Current Limitation

The main limitation is that screenshot robustness is demonstrated against the implemented screenshot-style redistribution simulation and related recovery path, not against every possible real-world display-camera capture pipeline. More advanced perspective distortion, moire effects, motion blur, and camera noise remain natural future work for a next-generation version.

## 10. Future Improvement

To further improve screenshot resistance, the following can be added:

- synchronization templates
- error-correcting code for watermark payload
- DWT + DCT hybrid embedding
- SVD-assisted embedding
- region-based repeated watermark groups
- screenshot-oriented geometric recovery

## 11. Conclusion

This project successfully demonstrates a secure digital document protection system with hybrid encryption, invisible watermarking, tamper detection, authenticity verification, and leak traceability. It supports offline, online-style, desktop upload-based, and web upload-based verification, and performs strongly against compression, cropping, scaling, screenshot-style redistribution, and minor editing in the implemented evaluation flow.
