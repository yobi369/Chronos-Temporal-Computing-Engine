# Machine-readable format schemas

These JSON Schema documents describe the supported serialized envelopes. They are published as documentation contracts; the Python readers remain authoritative for semantic validation and replay.

| Artifact | Schema | Compatibility |
|---|---|---|
| Event log | [event-log-v3.schema.json](event-log-v3.schema.json) | Event-log v3 only; v1/v2 remain supported by the runtime |
| Engine snapshot | [engine-snapshot-v2.schema.json](engine-snapshot-v2.schema.json) | Snapshot v2 envelope; flat v1 is migrated in memory |
| Timeline continuation | [timeline-continuation-v2.schema.json](timeline-continuation-v2.schema.json) | Continuation v2; v1 remains supported by the runtime |

## Validation

The documents use JSON Schema Draft 2020-12. Validate serialized files with a validator that supports that draft. Resolve referenced schemas relative to the schema document's published location.

These schemas describe structural shape and basic field constraints. They do not replace Chronos runtime validation of:

- canonical JSON restrictions (sorted keys, compact separators, finite numbers, string object keys, duplicate-key rejection);
- causal-parent relationships, event identity/sequence uniqueness, scheduler queue ordering, or event-history consistency;
- payload-specific required/optional property contracts stored in the event-log registry;
- cross-record digest consistency, fork lineage, deterministic handler execution, or replay equivalence.

In particular, the payload_schemas registry in event-log v3 is Chronos's compact payload-contract descriptor, not an embedded arbitrary JSON Schema document. Its supported type names are null, boolean, integer, number, string, array, and object. Chronos additionally rejects booleans where integer or number payload values are expected.

## Canonicalization and digests

JSON Schema does not define the byte representation used by Chronos digests. The runtime's canonicalization contract is documented in [event logs and replay](../event-logs-and-replay.md): UTF-8, lexicographically sorted object keys, compact separators, finite JSON-native values, and no implicit coercions. This is not a claim of RFC 8785/JCS compatibility.

SHA-256 fields are lowercase 64-character hexadecimal strings. A matching digest is a reproducibility consistency check, not a digital signature or authenticity guarantee.

## Versioning policy

Do not edit a published schema to describe an incompatible wire-format change. Add a new versioned schema document and preserve the existing schema and canonical golden fixtures. Event-log, snapshot, and timeline-continuation versions evolve independently.
