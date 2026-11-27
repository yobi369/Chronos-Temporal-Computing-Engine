# Canonical serialization and state digests

This document defines the canonical state-byte contract used by `state_digest` and the state-digest fields in event-log, snapshot, and timeline-continuation records. Other record-level digests (such as continuation checkpoint, history, and full-snapshot digests) cover their own canonical serialized records and are not identified by `STATE_DIGEST_FORMAT`. The current state encoding contract is identified as `chronos-canonical-json-v1`. It is a Chronos-specific encoding contract, **not** an assertion of RFC 8785 / JSON Canonicalization Scheme (JCS) compatibility.

## Canonical JSON v1

The implementation validates the value before encoding and then uses Python's standard JSON encoder with these exact settings:

- `ensure_ascii=False`: non-ASCII Unicode characters are emitted directly and the resulting text is encoded as UTF-8.
- `sort_keys=True`: object keys are sorted lexicographically by Python string ordering.
- `separators=(",", ":")`: no insignificant spaces are emitted.
- `allow_nan=False`: NaN and positive/negative infinity are rejected.
- Only JSON-native values are accepted: null, booleans, integers, finite floats, strings, lists, and dictionaries with string keys. Tuples, custom objects, non-string keys, and invalid UTF-8 strings are rejected. Values are not silently coerced.
- Duplicate object keys are rejected by the parser before a record is constructed.

Chronos does not normalize Unicode (for example, NFC and NFD strings remain distinct). Float spelling follows the supported Python JSON encoder behavior; negative zero is retained as `-0.0`. Cross-language consumers must use the published vectors and verify byte-for-byte compatibility rather than assuming that a generic JSON serializer is equivalent.

The public `canonical_json_bytes(value)` helper returns the exact UTF-8 bytes used by Chronos. `CANONICAL_JSON_FORMAT` identifies the encoding contract.

## State digest v1

`STATE_DIGEST_FORMAT` is `sha256(chronos-canonical-json-v1)`. The digest is calculated as:

1. Validate that the state is a JSON object with string keys.
2. Encode that object with Canonical JSON v1.
3. Encode the canonical text as UTF-8 bytes.
4. Compute SHA-256 directly over those bytes.
5. Render the result as 64 lowercase hexadecimal characters.

There is **no domain-separation prefix or additional envelope** in the hashed bytes. The hash covers only the canonical state object; it does not cover the timeline ID, event inputs, event history, payload-schema registry, event-log schema version, or file metadata. Those records are validated and compared separately during replay.

This is a reproducibility checksum, not a signature, MAC, authenticity proof, or tamper-proof audit chain. Anyone who can rewrite a log can also recompute an unkeyed SHA-256 digest.

All currently supported event-log schemas v1/v2/v3 use this same state-digest contract. Changing the canonical byte rules or digest algorithm would invalidate existing vectors and compatibility assumptions; do not silently change either. A future incompatible digest scheme must receive an explicit format/version transition and new golden vectors.

## Published test vectors

| State object | Canonical UTF-8 JSON | SHA-256 |
|---|---|---|
| `{}` | `{}` | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` |
| `{"z":[true,null,-0.0,1e-7],"é":"naïve","a":{"β":2}}` | `{"a":{"β":2},"z":[true,null,-0.0,1e-07],"é":"naïve"}` | `e830780abb737ef53eac4b0afdb3bea5e6cf040d94ef816fe5ac39f6c41d6ff4` |

The tests assert the actual UTF-8 bytes as well as the digest. The vectors cover sorted nested keys, direct Unicode encoding, booleans, null, negative zero, and exponent-form floats.

## Payload schemas and record versions

Event payload contracts are separate from canonicalization. Event-log v2 introduced the compact `PayloadSchema` registry; v3 retains it and adds the pre-first-dispatch initial state. Supported property types are `null`, `boolean`, `integer`, `number`, `string`, `array`, and `object`. Booleans are not accepted as integers or numbers. Required and optional fields are checked, and additional properties are rejected by default unless explicitly allowed.

The registry is intentionally a small object-validation contract, not a full JSON Schema engine. The machine-readable envelope schemas are in [`docs/schemas/`](schemas/README.md); runtime validation remains authoritative for payload values, event causality, history consistency, and replay.

## Reproducibility boundary

A matching state digest means the tested handler implementation reproduced the same canonical state bytes for the recorded inputs and execution history. It does not guarantee identical behavior across arbitrary Python implementations, dependency versions, external services, operating systems, or hidden process state. Record or control random seeds, wall-clock values, network responses, environment variables, files, and other external effects as explicit experiment inputs.

Physical time travel, relativistic manipulation, quantum-temporal effects, and closed timelike curves are not implemented by this serialization or replay system; they remain unimplemented research directions.
