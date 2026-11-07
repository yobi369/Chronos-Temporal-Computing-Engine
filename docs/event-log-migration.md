# Event-log schema migration

Use the explicit migration helper when an existing schema-v1 event log should be
rewritten as schema v2:

```python
from chronos.event_log_migration import migrate_event_log_v1_to_v2
from chronos import read_event_log, write_event_log

legacy = read_event_log("legacy.chronos.json")
current = migrate_event_log_v1_to_v2(legacy)
write_event_log("current.chronos.json", current)
```

Schema v1 did not contain payload contracts. Migration therefore creates a v2
log with an empty contract registry unless the caller supplies
`payload_schemas={event_type: PayloadSchema(...)}`. Supplied contracts are
validated against every initial input and observed event before a migrated
object is returned.

The helper is intentionally non-mutating: the original v1 object and source
file are unchanged. It rejects v2 inputs rather than silently treating an
already-current log as a migration. Both the source and result are validated
through the canonical event-log serializer. Migration changes the schema
envelope only; it does not rewrite event IDs, ordering, causal parent links,
payload values, or the recorded final-state digest.

Reading v1 remains supported. Migration is an explicit caller decision, not an
automatic side effect of reading or replaying a historical log.
