# Security Policy

Chronos is research software. Do not assume it is suitable for processing sensitive, regulated, or production-critical workloads without a deployment-specific security assessment.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in a public issue or pull request.

Use GitHub's **Report a vulnerability** / private vulnerability reporting feature for this repository when it is available. If private reporting is not enabled, contact the repository maintainer privately through a verified GitHub contact channel and request a secure disclosure route before sending exploit details.

Do not include credentials, private keys, customer data, or other secrets in a report.

A useful report includes:

- The affected commit, release, or branch.
- The affected component and configuration.
- Preconditions and a minimal reproduction.
- Expected and observed behavior.
- Potential impact and any known mitigations.

Please allow time for investigation and a coordinated fix before public disclosure. No response-time or remediation SLA is currently promised.

## Security boundaries

The following limitations are important:

- Replay invokes caller-registered handler code; it is not a sandbox.
- SHA-256 state and artifact digests are consistency checks, not proof of authenticity.
- Signed reports require reviewers to verify signatures against independently trusted public keys.
- HMAC-authenticated worker messages are not encrypted. Use TLS on untrusted networks and manage shared secrets securely.
- Worker inbox processing is at-least-once; handlers must be idempotent or implement transactional safeguards.
- Local persistence guarantees and filesystem durability depend on the documented single-writer protocol and platform behavior.
- Multi-tenant isolation, distributed consensus, leader election, and Byzantine fault tolerance are not provided.

Please do not use Chronos to process sensitive or production-critical data until the relevant security and operational controls have been independently assessed.
