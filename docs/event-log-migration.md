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

## Upgrade schema v2 to v3

Schema v3 adds the initial engine state so replay can reproduce experiments
that did not begin with an empty state. Schema v2 did not persist this value,
so migration requires the caller to supply the original state explicitly:

```python
from chronos import migrate_event_log_v2_to_v3, read_event_log, write_event_log

version_2 = read_event_log("version-2.chronos.json")
version_3 = migrate_event_log_v2_to_v3(
    version_2,
    initial_state={"opening_balance": 125},
)
write_event_log("version-3.chronos.json", version_3)
```

Pass `initial_state={}` only when the original run actually started empty.
Chronos cannot infer a historical starting state from the final digest, event
payloads, or observed history. A wrong supplied state will be detected when
replay compares the final state digest, but migration itself cannot prove that
the supplied state is historically correct.

For a v1 file, first migrate v1 to v2 with
`migrate_event_log_v1_to_v2`, then migrate that v2 object to v3 with the
original starting state. Both migrations return new validated objects and
leave the source object/file unchanged.

