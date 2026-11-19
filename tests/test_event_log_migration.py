import json

import pytest

from chronos.engine import SimulationEngine
from chronos.event_log import (
    EventInput,
    EventLog,
    EventLogError,
    PayloadSchema,
    event_log_from_json,
    event_log_to_json,
)
from chronos.event_log_migration import migrate_event_log_v1_to_v2


def build_run():
    engine = SimulationEngine("migration-fixture")

    def increment(event, simulation):
        simulation.state["total"] = simulation.state.get("total", 0) + event.payload["amount"]
        if event.payload.get("spawn"):
            simulation.schedule(event.time + 1, "increment", {"amount": 3})

    engine.register("increment", increment)
    inputs = (EventInput(2, "increment", {"amount": 4, "spawn": True}),)
    for item in inputs:
        engine.schedule(item.time, item.event_type, item.payload)
    engine.run()
    return engine, inputs


def legacy_log():
    engine, inputs = build_run()
    current = EventLog.capture(engine, inputs)
    document = json.loads(event_log_to_json(current))
    document["schema_version"] = 1
    document.pop("payload_schemas")
    document.pop("initial_state")
    return event_log_from_json(json.dumps(document))


def test_v1_migration_is_explicit_non_mutating_and_round_trips():
    legacy = legacy_log()
    legacy_json = event_log_to_json(legacy)
    migrated = migrate_event_log_v1_to_v2(legacy)

    assert legacy.schema_version == 1
    assert event_log_to_json(legacy) == legacy_json
    assert migrated.schema_version == 2
    assert migrated.timeline_id == legacy.timeline_id
    assert migrated.initial_events == legacy.initial_events
    assert migrated.events == legacy.events
    assert migrated.final_state_digest == legacy.final_state_digest
    assert event_log_from_json(event_log_to_json(migrated)) == migrated


def test_v1_migration_validates_optional_payload_contracts():
    legacy = legacy_log()
    schema = {
        "increment": PayloadSchema(
            required={"amount": "integer"},
            optional={"spawn": "boolean"},
        )
    }
    migrated = migrate_event_log_v1_to_v2(legacy, payload_schemas=schema)
    assert migrated.payload_schemas == schema

    invalid = {"increment": PayloadSchema(required={"missing": "string"})}
    with pytest.raises(EventLogError, match="missing required"):
        migrate_event_log_v1_to_v2(legacy, payload_schemas=invalid)


def test_migration_rejects_non_v1_input():
    legacy = legacy_log()
    current = EventLog(
        legacy.timeline_id,
        legacy.initial_events,
        legacy.events,
        legacy.final_state_digest,
        schema_version=2,
    )
    with pytest.raises(EventLogError, match="only schema version 1"):
        migrate_event_log_v1_to_v2(current)


def test_migration_rejects_non_event_log_input():
    with pytest.raises(TypeError, match="EventLog"):
        migrate_event_log_v1_to_v2(None)
