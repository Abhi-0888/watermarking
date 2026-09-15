# Literature Review — Secure Digital Document Protection and Traceability

Compact summary of related work and how this project addresses gaps identified in the literature.  
*Source: `Proposed_Project_Literature_Summary_Compact.docx`*

## Project Brief

This project protects digital documents and images using:

- **Encryption** — hybrid AES + RSA pipeline
- **Invisible personalized watermarking** — recipient-specific DCT-domain embedding
- **Integrity and authenticity verification** — SHA-256 hashing and digital signatures
- **Traceability of authorized transfers** — hash-linked provenance chain
- **Tamper localization** — block-level perceptual fingerprinting
- **Raspberry Pi verification interface** — lightweight hardware-assisted monitoring with LED status

See [README.md](../README.md) for implementation details and [PRESENTATION.md](PRESENTATION.md) for the demo guide.

## Related Work Comparison

| Citation | Use Case | Dataset | Methodology | Hardware | Limitations |
|----------|----------|---------|-------------|----------|-------------|
| Khafaga et al. (2023) | Secure transmission and authentication of color images | Color-image datasets; exact benchmark details require full paper review | Zero watermarking + Arnold scrambling + AES-CBC 256-bit encryption; attack testing | Raspberry Pi | Focuses mainly on image transmission; does not address document traversal/provenance history |
| d'Amore & Serpi (2021) | Leak/traitor tracing for sensitive PDF documents | PDF documents / document examples | Invisible watermarking with recipient-specific information for identifying leaked copies | Not hardware-focused | Primarily addresses traitor tracing; does not combine it with Raspberry Pi verification or transfer-history tracking |
| Gan et al. (2026) | Provenance tracing and tamper localization | Image datasets used for provenance/tamper experiments | GenPTW: latent-space watermarking with cross-attention and spatial fusion for provenance tracing and tamper localization | GPU-based research setup | Deep-learning based and comparatively complex; not focused on lightweight document-security hardware |
| Hosny et al. (2022) | Robust color-image watermarking with edge/hardware acceleration | Color-image datasets | Parallel QLFM watermarking with Arnold scrambling; MPI/OpenMP processing | Raspberry Pi 4B cluster | Hardware setup uses multiple Raspberry Pis; focuses on watermarking performance rather than end-to-end document lifecycle |
| Amrullah & Ernawan (2025/2026) | Tamper detection and localization | Image datasets; benchmark details depend on the full paper | Semi-fragile DCT watermarking using non-overlapping 8×8 blocks and coefficient quantization | Conventional computing platform | Mainly focused on image tamper localization; does not provide recipient/traversal tracking |
| Li et al. (2026) | Encrypted-image protection against forgery and redistribution | Image datasets / static images | Client-side watermarking, encrypted images, self-embedding and majority voting for tamper localization | Client-side computing; no Raspberry Pi focus | LSB-related cropping sensitivity; aggressive JPEG compression remains challenging; static images only |
| Sinha & Singh (2026) | Secure image watermarking for clinical-data provenance | Clinical/medical image datasets | Hybrid encryption with optimized/deep-learning based robust watermarking | GPU-oriented research environment | Designed for medical-image provenance and uses a relatively complex deep-learning pipeline |
| Zhang et al. (2025), OmniGuard | Copyright protection and hybrid tamper localization | Image datasets including degradation/editing evaluations | Deep image watermarking combining proactive embedding and passive manipulation localization | GPU-oriented research environment | Deep-learning approach with higher implementation complexity; not designed specifically for document-transfer tracking |
| Polenakis et al. (2025) | PDF authenticity and invisible watermarking | PDF documents | Invisible QR-code embedding in the spatial domain of PDF text color | Conventional computing platform | Focuses on PDF authenticity/watermarking; does not cover cryptographic transfer history or hardware-assisted verification |

## Research Gap

Existing work typically covers **one or two** of the following in isolation:

| Capability | Common in literature | This project |
|------------|---------------------|--------------|
| Hybrid encryption (AES + RSA) | Partial (Khafaga, Sinha & Singh) | ✓ |
| Recipient-specific watermarking / leak tracing | Partial (d'Amore & Serpi, Li et al.) | ✓ |
| Tamper localization | Partial (Gan, Amrullah & Ernawan, OmniGuard) | ✓ |
| Authorized transfer / traversal history | Rare | ✓ hash-linked provenance chain |
| Raspberry Pi verification terminal | Partial (Khafaga, Hosny) | ✓ single-Pi kiosk with LED + dashboard |
| End-to-end lifecycle (issue → transfer → verify → forensics) | Rare | ✓ |

## How This Implementation Maps to the Proposal

| Proposed feature | Module |
|------------------|--------|
| Hybrid encryption | `encryption/aes.py`, `encryption/rsa.py` |
| Invisible personalized watermarking | `watermark/embed.py`, `watermark/extract.py` |
| Integrity + authenticity | `utils/hash.py`, `verification/verify.py` |
| Transfer traceability | `provenance/chain.py`, `transfer.py` |
| Tamper localization | `verification/tamper_localization.py` |
| Raspberry Pi verification | `raspberry_pi/pi_verify_terminal.py` |
| Leak forensics | `utils/forensics.py` |

## Positioning Statement

> Unlike prior work that focuses on a single layer (encryption-only, watermark-only, or GPU-based deep learning), this project integrates classical cryptography, DCT watermarking, block-level tamper localization, hash-linked provenance, and a Raspberry Pi verification terminal into one lightweight, end-to-end pipeline suitable for academic demonstration and field verification without requiring GPU infrastructure.
