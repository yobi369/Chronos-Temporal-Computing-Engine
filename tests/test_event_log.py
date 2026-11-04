import json

import pytest

from chronos.engine import SimulationEngine
from chronos.event_log import (
    EventInput,
    EventLog,
    EventLogError,
    ReplayMismatchError,
    event_log_from_json,
    event_log_to_json,
    read_event_log,
    replay_event_log,
    state_digest,
    write_event_log,
)


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
    with pytest.raises(EventLogError, match="unsupported"):
        event_log_from_json('{"schema_version":2}')
    engine, inputs = build_run()
    document = json.loads(event_log_to_json(EventLog.capture(engine, inputs)))
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
