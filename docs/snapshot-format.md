# Snapshot format and migration policy

Snapshots are versioned independently from event logs. Version 2 uses a format identifier, schema version, writer metadata, and an engine payload containing timeline ID, logical time, sequence counter, pending queue, executed history, simulation state, and logical-clock value.

## Compatibility policy

- Writers emit only schema v2.
- Readers accept v2 and the documented legacy flat v1 envelope.
- v1 migrates in memory; loading does not rewrite the source file.
- Unknown future versions and unknown or missing fields fail closed.
- Migration preserves event IDs, ordering, queue, state, and clock counters.
- Every future schema requires a pure migration function and fixtures for each supported prior version.

Handler functions are excluded and must be registered after restoring an engine. Snapshots are not signed, encrypted, or a substitute for a transactional database.
