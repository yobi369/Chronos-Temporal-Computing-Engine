import json

import pytest

from chronos.engine import SimulationEngine
from chronos.event_log import (
    EventInput,
    EventLog,
    EventLogError,
    PayloadSchema,
    ReplayMismatchError,
    event_log_from_json,
    event_log_to_json,
    read_event_log,
    replay_event_log,
    state_digest,
    write_event_log,
)
from chronos.event_log_migration import migrate_event_log_v2_to_v3


def build_run():
    engine = SimulationEngine("experiment-a")

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


def handlers():
    def increment(event, simulation):
        simulation.state["total"] = simulation.state.get("total", 0) + event.payload["amount"]
        if event.payload.get("spawn"):
            simulation.schedule(event.time + 1, "increment", {"amount": 3})

    return {"increment": increment}


def test_canonical_json_round_trip_and_replay():
    engine, inputs = build_run()
    log = EventLog.capture(engine, inputs)
    encoded = event_log_to_json(log)
    assert encoded == event_log_to_json(event_log_from_json(encoded))
    replayed = replay_event_log(event_log_from_json(encoded), handlers())
    assert replayed.state == engine.state
    assert replayed.history == engine.history


def test_file_persistence_round_trip(tmp_path):
    engine, inputs = build_run()
    log = EventLog.capture(engine, inputs)
    target = tmp_path / "nested" / "experiment.json"
    write_event_log(target, log)
    assert read_event_log(target) == log


def test_replay_detects_state_tampering():
    engine, inputs = build_run()
    log = EventLog.capture(engine, inputs)
    altered = EventLog(
        log.timeline_id,
        log.initial_events,
        log.events,
        state_digest({"total": 999}),
    )
    with pytest.raises(ReplayMismatchError, match="state digest"):
        replay_event_log(altered, handlers())


def test_unsupported_version_and_unknown_fields_are_rejected():
    engine, inputs = build_run()
    document = json.loads(event_log_to_json(EventLog.capture(engine, inputs)))
    document["schema_version"] = 4
    with pytest.raises(EventLogError, match="unsupported"):
        event_log_from_json(json.dumps(document))
    document["schema_version"] = 3
    document["unexpected"] = True
    with pytest.raises(EventLogError, match="exactly"):
        event_log_from_json(json.dumps(document))


def test_duplicate_json_object_keys_are_rejected():
    with pytest.raises(EventLogError, match="duplicate JSON object key"):
        event_log_from_json('{"schema_version":1,"schema_version":1}')


def test_non_json_state_and_nan_payload_are_rejected():
    with pytest.raises(EventLogError, match="canonical JSON"):
        state_digest({"not_json": object()})
    engine, inputs = build_run()
    log = EventLog.capture(engine, inputs)
    encoded = event_log_to_json(log).replace('"amount":4', '"amount":NaN')
    with pytest.raises(EventLogError):
        event_log_from_json(encoded)


def test_oversized_file_is_rejected(tmp_path):
    target = tmp_path / "large.json"
    target.write_text("{}" * 100, encoding="utf-8")
    with pytest.raises(EventLogError, match="read limit"):
        read_event_log(target, max_bytes=10)


def test_payload_schemas_are_versioned_and_enforced_during_replay():
    engine, inputs = build_run()
    schemas = {
        "increment": PayloadSchema(
            required={"amount": "integer"},
            optional={"spawn": "boolean"},
        )
    }
    log = EventLog.capture(engine, inputs, payload_schemas=schemas)
    encoded = event_log_to_json(log)
    parsed = event_log_from_json(encoded)
    assert parsed.schema_version == 3
    assert parsed.payload_schemas == schemas
    assert replay_event_log(parsed, handlers()).state == engine.state


def test_payload_schema_rejects_wrong_types_and_undeclared_fields():
    engine, inputs = build_run()
    schemas = {"increment": PayloadSchema(required={"amount": "integer"})}
    log = EventLog.capture(engine, inputs, payload_schemas=schemas)
    invalid_input = EventInput(2, "increment", {"amount": True})
    invalid_log = EventLog(
        log.timeline_id,
        (invalid_input,),
        log.events,
        log.final_state_digest,
        payload_schemas=schemas,
    )
    with pytest.raises(EventLogError, match="must be integer"):
        event_log_to_json(invalid_log)

    extra_input = EventInput(2, "increment", {"amount": 4, "unlisted": "value"})
    invalid_log = EventLog(
        log.timeline_id,
        (extra_input,),
        log.events,
        log.final_state_digest,
        payload_schemas=schemas,
    )
    with pytest.raises(EventLogError, match="undeclared"):
        event_log_to_json(invalid_log)


def test_schema_v1_logs_remain_readable_and_round_trip_without_schema_metadata():
    engine, inputs = build_run()
    document = json.loads(event_log_to_json(EventLog.capture(engine, inputs)))
    document["schema_version"] = 1
    document.pop("payload_schemas")
    document.pop("initial_state")
    legacy = event_log_from_json(json.dumps(document))
    assert legacy.schema_version == 1
    assert legacy.payload_schemas == {}
    assert event_log_from_json(event_log_to_json(legacy)) == legacy


@pytest.mark.parametrize(
    "invalid_state",
    [
        {1: "non-string key"},
        {"tuple": (1, 2)},
        {"nested": {"bad": float("inf")}},
    ],
)
def test_state_digest_rejects_non_canonical_python_values(invalid_state):
    with pytest.raises(EventLogError):
        state_digest(invalid_state)


def test_non_standard_json_constants_are_rejected():
    with pytest.raises(EventLogError, match="non-standard JSON"):
        event_log_from_json('{"schema_version":NaN}')


def test_failed_atomic_replace_preserves_existing_file(tmp_path, monkeypatch):
    import chronos.event_log as event_log_module

    engine, inputs = build_run()
    target = tmp_path / "experiment.json"
    target.write_text("previous committed contents", encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(event_log_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        write_event_log(target, EventLog.capture(engine, inputs))

    assert target.read_text(encoding="utf-8") == "previous committed contents"
    assert list(tmp_path.glob(".experiment.json.*.tmp")) == []


def test_event_log_rejects_malformed_in_memory_event_fields():
    from dataclasses import replace

    engine, inputs = build_run()
    log = EventLog.capture(engine, inputs)
    malformed_event = replace(log.events[0], sequence=True)
    malformed = EventLog(
        log.timeline_id, log.initial_events, (malformed_event,),
        log.final_state_digest, payload_schemas=log.payload_schemas,
    )
    with pytest.raises(EventLogError, match="invalid fields"):
        event_log_to_json(malformed)


def test_deeply_nested_json_is_rejected_without_leaking_recursion_error():
    source = "[" * 1500 + "0" + "]" * 1500
    with pytest.raises(EventLogError):
        event_log_from_json(source)

    nested = {}
    cursor = nested
    for _ in range(1500):
        child = {}
        cursor["child"] = child
        cursor = child
    with pytest.raises(EventLogError, match="nesting depth"):
        state_digest(nested)


def test_persisted_event_log_rejects_invalid_utf8_and_truncated_json(tmp_path):
    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(bytes([0xFF]))
    with pytest.raises(EventLogError, match="UTF-8"):
        read_event_log(invalid_utf8)

    truncated = tmp_path / "truncated.json"
    truncated.write_text('{"schema_version":', encoding="utf-8")
    with pytest.raises(EventLogError, match="invalid event-log JSON"):
        read_event_log(truncated)



def test_schema_v2_logs_remain_readable_and_round_trip_without_initial_state():
    engine, inputs = build_run()
    document = json.loads(event_log_to_json(EventLog.capture(engine, inputs)))
    document["schema_version"] = 2
    document.pop("initial_state")
    legacy = event_log_from_json(json.dumps(document))

    assert legacy.schema_version == 2
    assert legacy.initial_state == {}
    assert event_log_from_json(event_log_to_json(legacy)) == legacy


def test_schema_v3_captures_non_empty_initial_state_and_replays():
    engine = SimulationEngine("initial-state-replay")
    engine.state = {"balance": 10}

    def credit(event, simulation):
        simulation.state["balance"] += event.payload["amount"]

    engine.register("credit", credit)
    inputs = (EventInput(4, "credit", {"amount": 5}),)
    for item in inputs:
        engine.schedule(item.time, item.event_type, item.payload)
    engine.run()

    log = EventLog.capture(engine, inputs)
    encoded = event_log_to_json(log)
    parsed = event_log_from_json(encoded)
    replayed = replay_event_log(parsed, {"credit": credit})

    assert parsed.schema_version == 3
    assert parsed.initial_state == {"balance": 10}
    assert replayed.state == {"balance": 15}
    assert replayed.state == engine.state


def test_schema_v2_migration_requires_and_preserves_supplied_initial_state():
    engine = SimulationEngine("v2-migration")
    engine.state = {"balance": 10}

    def credit(event, simulation):
        simulation.state["balance"] += event.payload["amount"]

    engine.register("credit", credit)
    inputs = (EventInput(2, "credit", {"amount": 7}),)
    for item in inputs:
        engine.schedule(item.time, item.event_type, item.payload)
    engine.run()
    captured = EventLog.capture(engine, inputs)

    legacy = EventLog(
        timeline_id=captured.timeline_id,
        initial_events=captured.initial_events,
        events=captured.events,
        final_state_digest=captured.final_state_digest,
        schema_version=2,
        payload_schemas=captured.payload_schemas,
    )
    migrated = migrate_event_log_v2_to_v3(
        legacy, initial_state={"balance": 10}
    )

    assert migrated.schema_version == 3
    assert migrated.initial_state == {"balance": 10}
    assert event_log_from_json(event_log_to_json(migrated)) == migrated
    assert replay_event_log(migrated, {"credit": credit}).state == engine.state


def test_schema_v3_rejects_non_json_initial_state():
    engine, inputs = build_run()
    captured = EventLog.capture(engine, inputs)
    invalid = EventLog(
        timeline_id=captured.timeline_id,
        initial_events=captured.initial_events,
        events=captured.events,
        final_state_digest=captured.final_state_digest,
        initial_state={"unsupported": object()},
    )
    with pytest.raises(EventLogError, match="canonical JSON"):
        event_log_to_json(invalid)


def test_event_input_detaches_nested_payload_from_constructor_argument():
    source = {"nested": {"items": [1, 2]}}
    item = EventInput(1, "increment", source)

    source["nested"]["items"].append(3)

    assert item.payload == {"nested": {"items": [1, 2]}}


def test_event_log_detaches_constructor_owned_inputs_events_and_state():
    from chronos.events import Event

    source_input_payload = {"nested": {"items": [1]}}
    source_event_payload = {"nested": {"items": [2]}}
    source_state = {"nested": {"value": 3}}
    initial_input = EventInput(1, "record", source_input_payload)
    observed_event = Event("root:0", 1, 0, "record", source_event_payload)
    log = EventLog(
        timeline_id="ownership",
        initial_events=(initial_input,),
        events=(observed_event,),
        final_state_digest=state_digest({"result": "fixed"}),
        initial_state=source_state,
    )

    source_input_payload["nested"]["items"].append(10)
    source_event_payload["nested"]["items"].append(20)
    source_state["nested"]["value"] = 30
    initial_input.payload["nested"]["items"].append(40)
    observed_event.payload["nested"]["items"].append(50)

    assert log.initial_events[0].payload == {"nested": {"items": [1]}}
    assert log.events[0].payload == {"nested": {"items": [2]}}
    assert log.initial_state == {"nested": {"value": 3}}
