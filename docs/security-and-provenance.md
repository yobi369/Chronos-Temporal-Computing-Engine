# Security and provenance model

**Status:** Early-stage engineering policy  
**Applies to:** Chronos serialized artifacts and portable experiment reports  
**Current report format:** Version 1

This document states what Chronos currently checks, what those checks do not establish, and the requirements for future authenticated provenance. It is not a security certification or a claim that Chronos is suitable for a regulated deployment.

## Security objectives

Chronos should make it possible for an engineer or reviewer to:
- detect accidental corruption or modification of a packaged artifact;
- validate supported artifact structure before consuming it;
- inspect useful metadata without printing simulation state or event payload values;
- reproduce an experiment when deterministic handlers, inputs, runtime assumptions, and dependencies are available;
- distinguish byte-integrity checks from proof of origin, identity, authorization, or scientific validity.

## Current guarantees

The current portable report workflow validates each supported event log or timeline continuation using the Chronos reader; copies it into a newly created report directory; validates the copy and compares its metadata summary with the source; records a SHA-256 digest; and verifies report format/version, relative artifact paths, file size, digest, runtime validity, and metadata summary on receipt.

The report verifier does not execute user handlers or replay a simulation. Replay is separate and requires the relevant deterministic handlers and controlled inputs.

The report generator refuses to overwrite an existing destination directory and stages output before publishing the completed directory. This reduces accidental partial output; it is not a defense against a malicious local process with write access to the same filesystem.

## Security properties not provided

A successful `chronos verify-report` result currently does **not** prove who created the report, that the report has not been maliciously replaced together with its artifacts, that an organization approved it, that a key or identity is trusted/current/authorized, that a simulation is scientifically valid or calibrated, that replay is equivalent, or that the host/runtime/dependencies/filesystem are uncompromised.

A SHA-256 digest stored beside the file it describes is useful for detecting accidental changes and mismatches. An attacker able to replace both the file and report can calculate a new digest. A digest is not a digital signature, trusted timestamp, or authenticated audit evidence.

## Threat model

The current verifier is designed primarily for benign transfer and review workflows where the report manifest is not assumed to be adversarially controlled.

| Threat | Current mitigation | Remaining limitation |
|---|---|---|
| Accidental artifact corruption in transit | SHA-256 comparison | Does not authenticate the sender |
| Malformed or unsupported artifact | Chronos reader validation | Parser and runtime defects remain possible |
| Path traversal through manifest paths | Restricts paths to a direct child of artifacts/ and checks resolved containment | Does not protect against every concurrent filesystem race or hostile filesystem |
| Oversized artifact input | Supported artifact size limit | Resource exhaustion may still arise elsewhere |
| Sensitive payload disclosure through summaries | Summaries expose metadata and field names, not payload values | Bundled original artifacts still contain their original data; review before sharing |
| Replacement of manifest and artifacts by one attacker | Not mitigated by unsigned format | Requires independently trusted signature verification and key policy |

The report bundle should be treated as potentially sensitive because original event logs and continuations are included. Review artifacts before sharing them externally. Do not place secrets, credentials, personal data, or production customer data in an experiment unless data handling and authorization requirements have been assessed.

## Signed provenance design

The accepted version-1 design is documented in [Signed report format](signed-report-format.md). It specifies Ed25519 via the optional `cryptography` dependency, exact-byte signing of `report.json`, a detached `signature.json` envelope, externally managed PEM keys, and separate signature-validity and trust outcomes.

The design intentionally does not claim identity verification, organizational authorization, trusted timestamps, revocation, expiry, or automated key rotation. A valid signature from an unknown key must be reported as valid but untrusted. Private keys remain outside report bundles and outside Chronos-managed storage.

**Implementation status:** Signing and verification commands are not yet implemented. Until the implementation and full CI matrix pass, describe report verification only as structural validation and SHA-256 integrity checking. Do not describe report bundles as signed, authenticated, tamper-proof, compliant, or independently certified.

## Related documentation

- [Portable experiment reports](experiment-reports.md)
- [Signed report format](signed-report-format.md)
- [Machine-readable format schemas](schemas/README.md)
- [Event logs and replay](event-logs-and-replay.md)
