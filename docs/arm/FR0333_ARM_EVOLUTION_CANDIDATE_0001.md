# FR0333 ARM Evolution Candidate 0001
Version: 0.1.0
Date: 2026-10-08
State: PROPOSED / RUNTIME HOLD
HumanLock: REQUIRED before operational promotion

## Purpose
Evaluate security and resilience improvements suggested by pwn.college ARM Architecture, XNU Dojo, Fuzz Dojo, Content Injection, and Adversarial Machine Learning exercises. External training content is reference material, not evidence of FR0333 implementation.

## Source tabs
TAB.01 https://pwn.college/arm-architecture/
TAB.02 https://pwn.college/xnu/
TAB.03 https://pwn.college/dojos
TAB.04 https://www.arm.com/architecture/cpu/a-profile/armv9

## Candidate PINs
PIN.ARM.0001: Discover actual execution architecture and platform capabilities before requiring ARM-only controls.
PIN.ARM.0002: Evaluate PAC, BTI, MTE support separately; unsupported hardware must report NOT_APPLICABLE, never PASS.
PIN.ARM.0003: Evaluate RME/CCA isolation only on supported platforms with verifiable attestation and threat model.
PIN.ARM.0004: Add deterministic fuzzing seeds, crash reproduction, and minimization to eligible parsers.
PIN.ARM.0005: Test injection defenses at untrusted-content and tool boundaries; never grant training examples authority.
PIN.ARM.0006: Preserve provenance, toolchain versions, test environment, timestamps, and signed receipts where supported.
PIN.ARM.0007: Baseline before changes; compute observed delta only from comparable tests.
PIN.ARM.0008: No production claims or merge without HumanLock, CI evidence, and independent review.

## Test matrix (proposed, not executed)
T01 Platform inventory and ARM64 capability detection.
T02 PAC / BTI / MTE availability versus enabled state.
T03 Isolation and permission-boundary negative tests.
T04 Fuzz harness with reproducible corpus and crash artifacts.
T05 Prompt/content injection regression cases.
T06 CI receipt schema, tamper checks, and comparison against baseline.

## Acceptance
Each test needs source revision, command, platform, observed result, expected result, timestamp, and receipt link. Unsupported features report HOLD/NOT_APPLICABLE. Any failing mandatory test blocks promotion.

## Evolution gate
SOURCE -> ARCHITECTURE -> CAPABILITY -> TEST -> DELTA -> HUMANLOCK -> PROMOTE/HOLD -> STAY

## Change history (append-only)
2026-10-08: Initial research candidate registered. No runtime implementation or certification claimed.
