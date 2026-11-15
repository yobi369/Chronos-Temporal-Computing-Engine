# Signed report format

**Status:** Implemented on the development branch; release validation remains open  
**Scope:** Portable Chronos experiment reports  
**Signing format:** Version 1

This format separates cryptographic signature validity from a recipient's trust policy.

## Decision and implementation

- Ed25519 signatures use the maintained cryptography Python package.
- cryptography remains optional; the package exposes a signing extra.
- The signed object is the exact byte sequence of report.json as written to disk. Verification does not parse and reserialize the manifest before checking the signature.
- The detached signature and public verification key are stored in signature.json. Private key material is never included in a report.
- Signing accepts an externally managed PEM Ed25519 private key. Verification accepts an optional PEM public key as the recipient's explicit trust input.
- The key identifier is the lowercase hexadecimal SHA-256 digest of the raw 32-byte Ed25519 public key.
- Signature validity and trust status are reported independently.

## Signed bytes

The signed message is:

    ASCII("CHRONOS-REPORT-SIGNATURE") || 0x00 || ASCII("v1") || 0x00 || exact report.json bytes

The domain separator prevents this signature from being confused with a signature over another Chronos object type. The exact-byte rule means whitespace changes to report.json invalidate the signature. This format does not claim canonical JSON serialization.

## Detached envelope

signature.json is UTF-8 JSON with these version-1 fields:

    {
      "format": "chronos-report-signature",
      "version": 1,
      "algorithm": "Ed25519",
      "key_id": "<64 lowercase hexadecimal characters>",
      "public_key": "<base64 of 32 raw Ed25519 public-key bytes>",
      "report_sha256": "<64 lowercase hexadecimal characters>",
      "signature": "<base64 of 64 Ed25519 signature bytes>"
    }

The verifier reads a bounded signature envelope (16 KiB maximum), requires UTF-8 JSON, and rejects duplicate or unknown fields, non-standard JSON constants, unsupported versions and algorithms, invalid key identifiers or report digests, malformed or non-canonical base64, incorrect key/signature lengths, key-ID mismatches, manifest digest mismatches, and invalid signatures. PEM key inputs are limited to 64 KiB. These bounds apply to the signature envelope and key files; they are not a general sandbox or a bound on report-manifest size.

The public key is embedded to permit cryptographic verification without a network lookup. Its presence does not make it trusted.

## Trust policy

- A mathematically valid signature with no matching trusted public key is **valid but untrusted**.
- A signature is **trusted** only when the embedded raw public key exactly matches a PEM public key explicitly supplied by the reviewer.
- A trusted-key match is a local policy decision. It is not proof of legal identity, organizational authorization, key custody, or current key status.
- Version 1 has no online certificate discovery, revocation, expiry, trusted timestamp, organization directory, or automated key rotation.
- Invalid signatures and manifest digest mismatches fail verification. An unknown signing key does not become trusted merely because its signature is mathematically valid.

## CLI

Create a signed report:

    chronos create-report --output-dir review-bundle --continuation experiment.continuation.json --signing-key /secure/path/reviewer-private.pem

Verify cryptographic validity:

    chronos verify-report review-bundle

Verify and make an explicit local trust decision:

    chronos verify-report review-bundle --trusted-public-key /secure/path/reviewer-public.pem

Encrypted PEM private keys prompt for a passphrase. Passphrases are not command-line arguments and are not logged. Chronos does not generate, persist, upload, print, or bundle private keys.

For a signed report without a trusted public key, verification returns signature_valid=true and trust_status=untrusted. The CLI's successful exit status means the report structure, artifact integrity, and signature are valid; it does not mean the signer is trusted. Automation that requires a trusted signer must inspect trust_status or provide the expected key.

## Tests and release validation

The current test suite covers signing and verification with generated Ed25519 keys, valid-but-untrusted status, exact-key trust matching, wrong-key behavior, manifest tampering, duplicate fields, invalid UTF-8, non-standard JSON constants, envelope/key-file size limits, unsupported version/algorithm values, key-ID mismatch, malformed base64 and lengths, signature-byte tampering, encrypted-key passphrase prompting, private-key exclusion from the envelope, and unsigned-report compatibility.

Before a release, extend negative-format coverage to include deterministic test vectors, duplicate fields, unsupported version/algorithm values, malformed base64 and lengths, key-ID mismatch, signature-byte tampering, encrypted-key prompting, and operation without the optional dependency. Run the complete supported OS/Python CI matrix and perform an independent security review of key handling.

## Security boundary

This format signs the report manifest, which binds artifact paths, hashes, types, and metadata summaries. It does not establish a real-world identity, authorization, trusted time, revocation status, scientific correctness, simulation replay, or host integrity. It is not a compliance certification or a substitute for managed organizational key custody.
