# Security and provenance model

**Status:** Early-stage engineering policy  
**Applies to:** Chronos serialized artifacts and portable experiment reports  
**Current report format:** Version 1

This document states what Chronos currently checks and what those checks do not establish. It is not a security certification or a claim that Chronos is suitable for a regulated deployment.

## Security objectives

Chronos should make it possible for an engineer or reviewer to:
- detect accidental corruption or modification of a packaged artifact;
- validate supported artifact structure before consuming it;
- inspect useful metadata without printing simulation state or event payload values;
- reproduce an experiment when deterministic handlers, inputs, runtime assumptions, and dependencies are available;
- distinguish byte integrity, cryptographic authenticity, local key trust, and scientific validity.

## Current guarantees

The portable report workflow validates each supported event log or timeline continuation using the Chronos reader; copies it into a newly created report directory; validates the copy and compares its metadata summary with the source; records a SHA-256 digest; and verifies report format/version, relative artifact paths, file size, digest, runtime validity, and metadata summary on receipt. The report manifest itself is limited to 4 MiB and must be UTF-8 JSON with unique object keys and standard JSON constants; excessive nesting is rejected. Artifact references must use canonical direct-child paths under artifacts/ and resolve to distinct files inside the report directory.

When a detached signature is present, Chronos verifies an Ed25519 signature over the exact bytes of report.json. The manifest binds the relative artifact paths, SHA-256 digests, artifact types, and metadata summaries. Signature validity is reported separately from trust status.

A report is **trusted** only when the embedded public key exactly matches a PEM public key explicitly supplied by the reviewer. Without that trust input, a mathematically valid signature is reported as valid but untrusted. A successful CLI exit in that case means cryptographic and structural checks passed; it does not mean the signer is trusted.

The report generator refuses to overwrite an existing destination directory and stages output before publishing the completed directory. This reduces accidental partial output; it is not a defense against a malicious local process with write access to the same filesystem.

## Security properties not provided

Chronos does not establish a real-world identity, legal authorship, organizational authorization, key custody, trusted time, key revocation, expiry, or automated rotation. The embedded public key is self-asserted unless the reviewer checks it against an independently obtained trusted key. A valid signature from an unknown key must not be treated as trusted provenance.

A SHA-256 digest stored beside the file it describes detects accidental changes and mismatches relative to the manifest. By itself, it does not authenticate the sender. An attacker who can replace both an unsigned report and its artifacts can calculate new hashes. A signature helps detect replacement only when the reviewer checks it against a separately trusted public key and the signing private key has not been compromised.

Report verification does not execute user handlers or replay a simulation. It does not independently validate model assumptions, calibrate a scientific model, prove that a scenario is realistic, or establish that a replay is equivalent. Replay remains a separate workflow requiring the relevant deterministic handlers and controlled inputs.

## Threat model

The report verifier is designed for bounded artifact validation and review. It is not a sandbox for arbitrary handlers or a defense against a compromised host.

| Threat | Current mitigation | Remaining limitation |
|---|---|---|
| Accidental artifact corruption in transit | SHA-256 comparison against report manifest | Does not authenticate the sender |
| Manifest or artifact replacement | Detached Ed25519 signature over the manifest; reviewer-supplied trusted key | No protection if the private key is compromised or the reviewer accepts an unknown key |
| Malformed or unsupported artifact | Chronos reader validation | Parser and runtime defects remain possible |
| Malformed or ambiguous report manifest | 4 MiB bounded read; UTF-8 decoding; duplicate-key and non-standard-constant rejection; excessive nesting handled as a controlled error | Does not eliminate parser defects or every concurrent filesystem race |
| Path traversal through manifest paths | Restricts paths to a direct child of artifacts/ and checks resolved containment | Does not protect against every concurrent filesystem race or hostile filesystem |
| Oversized artifact input | Supported artifact size limit | Resource exhaustion may still arise elsewhere |
| Sensitive payload disclosure | Metadata summaries omit payload/state values | Original event logs and continuations are included unchanged and may contain sensitive data |
| Private signing-key compromise | Keys remain externally managed and outside report bundles | Key custody, rotation, revocation, and incident response are outside Chronos |

The report bundle should be treated as potentially sensitive because original event logs and continuations are included. Review artifacts before sharing them externally. Do not place secrets, credentials, personal data, or production customer data in an experiment unless data handling and authorization requirements have been assessed.

## Signed provenance format

The version-1 Ed25519 envelope and exact-byte signing rules are specified in [Signed report format](signed-report-format.md). Signing is optional and uses the cryptography dependency extra. The CLI does not generate or store private keys. There is no online certificate discovery, revocation, expiry, trusted timestamp, organization directory, or automated key rotation.

## Related documentation

- [Command-line interface](cli.md)
- [Portable experiment reports](experiment-reports.md)
- [Signed report format](signed-report-format.md)
- [Machine-readable format schemas](schemas/README.md)
- [Event logs and replay](event-logs-and-replay.md)
