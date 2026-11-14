"""Explicit migration helpers for versioned Chronos event logs."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronos.event_log import (
    EventLog,
    EventLogError,
    PAYLOAD_SCHEMA_VERSION,
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
        schema_version=PAYLOAD_SCHEMA_VERSION,
        payload_schemas=schemas,
    )
    # Validate the destination, including any newly supplied payload contracts.
    event_log_to_json(migrated)
    return migrated


def migrate_event_log_v2_to_v3(
    log: EventLog,
    *,
    initial_state: Mapping[str, Any],
) -> EventLog:
    """Return a validated v3 copy, requiring the original pre-execution state.

    Version 2 did not persist initial state. Migration cannot infer it from the
    final state or event history, so callers must provide the state that existed
    immediately before the first event was dispatched.
    """
    if not isinstance(log, EventLog):
        raise TypeError("log must be an EventLog")
    if log.schema_version != PAYLOAD_SCHEMA_VERSION:
        raise EventLogError("only schema version 2 event logs can be migrated to version 3")
    if not isinstance(initial_state, Mapping):
        raise TypeError("initial_state must be a mapping")

    # Validate the source and the caller-supplied destination independently.
    event_log_to_json(log)
    migrated = EventLog(
        timeline_id=log.timeline_id,
        initial_events=log.initial_events,
        events=log.events,
        final_state_digest=log.final_state_digest,
        schema_version=SCHEMA_VERSION,
        payload_schemas=log.payload_schemas,
        initial_state=dict(initial_state),
    )
    event_log_to_json(migrated)
    return migrated
