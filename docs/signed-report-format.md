# Signed report format and implementation decision

**Status:** Accepted design; implementation pending  
**Scope:** Portable Chronos experiment reports  
**Signing format:** Version 1

This decision defines the first supported signed-report profile. It deliberately separates mathematical signature validity from a recipient's trust policy.

## Decision

- Use Ed25519 signatures through the maintained `cryptography` Python package.
- Keep `cryptography` optional so the Chronos core remains dependency-free. Expose a `signing` extra.
- Keep the existing report manifest (`report.json`) as the signed object. Sign its exact bytes as written to disk; do not parse and reserialize it during verification.
- Store the detached signature and public verification key in `signature.json`. Never include private key material in a report.
- Accept externally managed PEM private keys for signing and PEM public keys as recipient trust inputs.
- Compute the key identifier as the lowercase hexadecimal SHA-256 digest of the Ed25519 raw 32-byte public key.
- Report signature validity and trust status independently.

## Signed bytes

The signed message is the following byte concatenation:

```text
ASCII("CHRONOS-REPORT-SIGNATURE") || 0x00 || ASCII("v1") || 0x00 || exact report.json bytes
```

The domain separator prevents the signature from being confused with a signature over another Chronos object type. The manifest already binds each artifact's relative path, SHA-256 digest, type, and metadata summary. The exact-byte rule means whitespace changes to `report.json` invalidate the signature; no JSON canonicalization claim is made.

## Detached envelope

`signature.json` is UTF-8 JSON with this version-1 shape:

```json
{
  "format": "chronos-report-signature",
  "version": 1,
  "algorithm": "Ed25519",
  "key_id": "<64 lowercase hexadecimal characters>",
  "public_key": "<base64 of 32 raw Ed25519 public-key bytes>",
  "report_sha256": "<64 lowercase hexadecimal characters>",
  "signature": "<base64 of 64 Ed25519 signature bytes>"
}
```

The verifier must reject wrong types, unsupported versions/algorithms, malformed or non-canonical base64, incorrect key/signature lengths, invalid key identifiers, and unknown envelope fields. It must recompute both the key identifier and report digest. The signature is verified over the domain-separated exact manifest bytes.

The public key is included to permit cryptographic verification without a network lookup. Its presence does not make it trusted.

## Trust policy

- A mathematically valid signature with no matching trusted public key is **valid but untrusted**.
- A signature is **trusted** only when its derived key identifier and raw public key exactly match a public key supplied through an explicit local trust input.
- A trusted-key match is a local policy decision, not proof of legal identity, organizational authorization, key custody, or current key status.
- Version 1 has no online certificate discovery, revocation, expiry, trusted timestamp, organization directory, or automated key rotation. The CLI must state these limitations.
- Invalid signatures and manifest digest mismatches fail verification. Unknown signing keys do not turn a valid signature into a trusted one.

## CLI contract

Planned commands:

```sh
chronos create-report --output-dir review-bundle \
  --continuation experiment.continuation.json \
  --signing-key /secure/path/reviewer-ed25519-private.pem

chronos verify-report review-bundle
chronos verify-report review-bundle \
  --trusted-public-key /secure/path/reviewer-ed25519-public.pem
```

Signing must fail clearly if the optional dependency is absent, the key is not Ed25519, or the key cannot be loaded. The user supplies the key; Chronos must not generate, persist, upload, print, or bundle private keys. Key passphrases must never be accepted as command-line arguments or logged.

Verification of an unsigned legacy report remains supported. Verification of a signed report without a trusted key may report cryptographic validity while explicitly returning an untrusted trust status. JSON output must keep `integrity_verified`, `signature_valid`, and `trust_status` as separate fields.

## Required tests

- Known deterministic Ed25519 test vector for the domain-separated message.
- Sign and verify with matching key.
- Valid signature with no trust input reports untrusted.
- Valid signature with matching trust input reports trusted.
- Wrong trusted key remains untrusted.
- Manifest byte change, artifact tampering, signature tampering, and wrong key fail safely.
- Malformed envelope, duplicate/unknown fields, unsupported algorithm/version, invalid base64, wrong key/signature lengths, and key-ID mismatch are rejected.
- Unsigned report compatibility remains intact.
- Private key bytes never appear in report contents or CLI output.
- Cross-platform CI covers supported Python versions.

## Security boundary

This format provides a detached Ed25519 signature over a report manifest and a local key-match trust decision. It does not establish a real-world identity, authorization, trusted time, revocation status, scientific correctness, simulation replay, or host integrity. It is not a compliance certification or a substitute for managed organizational key custody.

## Implementation gate

Do not advertise signed reports until the implementation, dependency extra, CLI, tests, and user documentation all land and the full CI matrix passes.
