"""Explicit migration helpers for versioned Chronos event logs."""
from __future__ import annotations

from collections.abc import Mapping

from chronos.event_log import (
    EventLog,
    EventLogError,
    PayloadSchema,
    SCHEMA_VERSION,
    event_log_to_json,
)


def migrate_event_log_v1_to_v2(
    log: EventLog,
    *,
    payload_schemas: Mapping[str, PayloadSchema] | None = None,
) -> EventLog:
    """Return a validated v2 copy of a v1 log without modifying the source.

    Schema v1 did not carry payload contracts. Callers may supply contracts
    during migration; when supplied, they are validated against every recorded
    input and observed event before the migrated log is returned.
    """
    if not isinstance(log, EventLog):
        raise TypeError("log must be an EventLog")
    if log.schema_version != 1:
        raise EventLogError("only schema version 1 event logs can be migrated to version 2")

    # Validate the source using the same public serializer used for persistence.
    event_log_to_json(log)
    schemas = dict(payload_schemas or {})
    migrated = EventLog(
        timeline_id=log.timeline_id,
        initial_events=log.initial_events,
        events=log.events,
        final_state_digest=log.final_state_digest,
        schema_version=SCHEMA_VERSION,
        payload_schemas=schemas,
    )
    # Validate the destination, including any newly supplied payload contracts.
    event_log_to_json(migrated)
    return migrated
