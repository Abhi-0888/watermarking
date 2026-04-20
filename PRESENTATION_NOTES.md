# Presentation Notes

## Slide 1: Title

Secure Digital Document Protection System

One-line intro:

"This project protects digital documents using encryption, invisible watermarking, tamper detection, and forensic traceability."

## Slide 2: Problem

Digital documents can be:

- leaked
- tampered with
- redistributed without authorization
- difficult to verify offline

Goal:

"Build a system that can protect, verify, and trace a digital document."

## Slide 3: Objectives

- ensure confidentiality
- ensure authenticity
- detect tampering
- identify leaked recipient copies
- support offline and online verification

## Slide 4: Technologies Used

- Python
- OpenCV
- NumPy
- AES
- RSA
- SHA-256
- Digital Signature
- DCT Watermarking

## Slide 5: Architecture

Pipeline:

1. input document
2. AES encryption
3. RSA key protection
4. watermark embedding
5. hash + signature
6. manifest / registry generation
7. verification
8. forensic tracing

## Slide 6: Cryptographic Layer

Explain:

- AES encrypts the file
- RSA protects the AES key
- SHA-256 creates file fingerprint
- digital signature proves authenticity

Line to say:

"AES protects the content, RSA protects the key, and the signature proves the document is genuine."

## Slide 7: Watermarking Layer

Explain:

- invisible watermark is embedded in DCT coefficients
- watermark contains issuer, receiver, document ID, and timestamp
- repeated embedding gives redundancy

Line to say:

"Even if the file is redistributed, the hidden identity of the recipient can be recovered from the watermarked copy."

## Slide 8: Verification

Offline mode:

- verify using local manifest

Online mode:

- verify using manifest + registry

Desktop verifier:

- upload protected file and manifest using `python gui_verify.py`

Web verifier:

- upload protected file and manifest using `python web_verify.py`
- dependency-free, uses Python standard library only

Checks:

- hash check
- signature check
- watermark check
- registry check in online mode

## Slide 9: Leak Traceability

Explain:

- extract watermark from leaked copy
- identify recipient
- produce forensic report

Line to say:

"If a protected copy leaks, the system can identify the intended recipient of that copy."

## Slide 10: Attack Simulation

Attacks tested:

- compression
- cropping
- scaling
- screenshot
- minor edits

Execution note:

- `python main.py present` is used for live demo
- `python main.py full` is used for complete evaluation output

## Slide 11: Results

Final result summary:

- compression: PASS
- cropping: PASS
- scaling: PASS
- minor edit: PASS
- screenshot: PASS

Metrics:

- PSNR: 21.76 dB
- encryption time: 8.93 ms
- extraction accuracy: 1.0
- false positive rate: 0.0
- attack pass rate: 1.0

Runtime:

- presentation mode: about 5 seconds
- full mode: about 40 seconds

## Slide 12: Honest Limitation

Line to say:

"The current implementation survives compression, cropping, scaling, screenshot-style redistribution, and minor edits in our evaluation flow. More advanced real-world camera-display screenshot variations can still be considered future improvement."

## Slide 13: Future Scope

- DWT + DCT watermarking
- error-correcting codes
- synchronization markers
- stronger real-world screenshot recovery
- web upload verifier interface

## Slide 14: Conclusion

Line to say:

"The project successfully combines security, verification, and traceability into one system, and demonstrates a strong practical prototype for secure digital document protection with end-to-end verification and robust evaluation."
