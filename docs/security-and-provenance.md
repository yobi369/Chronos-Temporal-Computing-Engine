# Security and provenance model

**Status:** Early-stage engineering policy  
**Applies to:** Chronos serialized artifacts and portable experiment reports  
**Current report format:** Version 1

This document states what Chronos currently checks, what those checks do not establish, and the requirements for any future authenticated-provenance feature. It is not a security certification or a claim that Chronos is suitable for a regulated deployment.

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

A successful `chronos verify-report` result does **not** prove who created the report, that the report has not been maliciously replaced together with its artifacts, that an organization approved it, that a key or identity is trusted/current/authorized, that a simulation is scientifically valid or calibrated, that replay is equivalent, or that the host/runtime/dependencies/filesystem are uncompromised.

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

## Future authenticated provenance: design requirements

No signing or verification command is currently implemented. The following requirements must be met before Chronos advertises signed reports.

### Signed object and canonical representation

- Sign a narrowly defined manifest payload, not an ambiguous re-serialization of arbitrary JSON.
- Specify exact signed bytes, including UTF-8 encoding, field inclusion, ordering, and newline rules.
- Bind report format/schema version, Chronos version, artifact paths, artifact sizes, and SHA-256 digests into the signed payload.
- Reject duplicate artifact paths, unsupported algorithms, malformed encodings, and unknown critical fields.
- Version the signing envelope independently so algorithms and formats can evolve without silently changing verification semantics.
- Do not claim RFC 8785/JCS compatibility unless the implementation conforms and has conformance tests.

### Cryptography and key custody

- Use a mature, maintained cryptographic library or established signing tool; do not implement cryptographic primitives in Chronos.
- Prefer a documented public-key signature scheme with explicit algorithm identifiers and test vectors.
- Keep private keys outside report bundles. Never generate or silently persist a long-lived private key on behalf of a user.
- Support externally managed keys and hardware-backed custody where practical.
- Include a stable key identifier derived from the public key, not a user-controlled display name.
- Treat key rotation, compromise, revocation, expiry, and trust-store updates as explicit operational policy, not properties inferred from a mathematically valid signature.

### Verification policy

Verification must report separate outcomes for integrity, signature validity, trust decision, key status, and freshness. A valid signature from an unknown key must not be reported as trusted. If revocation information is unavailable, the verifier must say so rather than implying that the key is current. A locally supplied trust store is policy input and must itself be protected and governed.

### Operational controls

Before release, the feature requires published format and threat-model documentation; positive, negative, tampering, malformed-input, wrong-key, unknown-key, revoked-key, and algorithm-mismatch tests; cross-platform tests and deterministic test vectors; review of dependency maintenance, licensing, and supported Python versions; explicit CLI output distinguishing cryptographic validity from trust; no private-key material in logs, reports, fixtures, or CI artifacts; and a migration policy for older unsigned reports.

## Release gate

Authenticated provenance remains **not implemented** until the design above is implemented, reviewed, tested, and documented. Until then, describe Chronos report verification only as structural validation and SHA-256 integrity checking. Do not describe report bundles as signed, authenticated, tamper-proof, compliant, or independently certified.

## Related documentation

- [Portable experiment reports](experiment-reports.md)
- [Machine-readable format schemas](schemas/README.md)
- [Event logs and replay](event-logs-and-replay.md)
