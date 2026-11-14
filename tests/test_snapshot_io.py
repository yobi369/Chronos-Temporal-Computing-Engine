import json
import pytest
from chronos.engine import SimulationEngine
from chronos.event_log import EventLogError
from chronos.snapshot_io import snapshot_from_json, snapshot_to_json

def engine_snapshot():
    engine = SimulationEngine("snapshot-test")
    engine.register("noop", lambda event, _: None)
    engine.schedule(5, "noop", {"value": 1})
    engine.state["counter"] = 7
    return engine.snapshot()

def test_v2_snapshot_round_trip():
    snapshot = engine_snapshot()
    assert snapshot_from_json(snapshot_to_json(snapshot)) == snapshot

def test_v1_snapshot_migrates_to_v2_shape():
    snapshot = engine_snapshot()
    legacy = {"schema_version": 1, "timeline_id": snapshot.timeline_id,
        "current_time": snapshot.current_time, "next_sequence": snapshot.next_sequence,
        "queue": [{"event_id": e.event_id, "time": e.time, "sequence": e.sequence,
            "event_type": e.event_type, "payload": e.payload,
            "parent_event_id": e.parent_event_id} for e in snapshot.queue],
        "history": [], "state": snapshot.state,
        "logical_clock_value": snapshot.logical_clock_value}
    assert snapshot_from_json(json.dumps(legacy)) == snapshot

def test_unsupported_and_corrupt_snapshots_are_rejected():
    with pytest.raises(EventLogError, match="unsupported"):
        snapshot_from_json('{"schema_version":99}')
    document = json.loads(snapshot_to_json(engine_snapshot()))
    document["engine"]["next_sequence"] = 0
    with pytest.raises(EventLogError, match="next_sequence"):
        snapshot_from_json(json.dumps(document))


def test_snapshot_rejects_duplicate_event_ids_across_queue_and_history():
    from dataclasses import replace

    snapshot = engine_snapshot()
    queued = snapshot.queue[0]
    historical = replace(queued, time=0, sequence=0)
    queued = replace(queued, sequence=1)
    malformed = replace(snapshot, queue=(queued,), history=(historical,), next_sequence=2)
    with pytest.raises(EventLogError, match="duplicate event IDs"):
        snapshot_from_json(snapshot_to_json(malformed))


def test_snapshot_constructor_detaches_nested_state_and_event_payloads():
    from chronos.engine import EngineSnapshot
    from chronos.events import Event

    source_state = {"nested": {"values": [1]}}
    source_event_payload = {"nested": {"values": [2]}}
    queued = Event("snapshot:0", 5, 0, "noop", source_event_payload)
    snapshot = EngineSnapshot(
        "snapshot",
        0,
        1,
        (queued,),
        (),
        source_state,
        0,
    )

    source_state["nested"]["values"].append(3)
    source_event_payload["nested"]["values"].append(4)

    assert snapshot.state == {"nested": {"values": [1]}}
    assert snapshot.queue[0].payload == {"nested": {"values": [2]}}


def test_snapshot_rejects_non_standard_json_numeric_constants():
    source = snapshot_to_json(engine_snapshot()).replace('"counter":7', '"counter":NaN')
    with pytest.raises(EventLogError, match="non-standard JSON numeric constant"):
        snapshot_from_json(source)


def test_snapshot_rejects_excessive_json_nesting_cleanly():
    snapshot = engine_snapshot()
    source = snapshot_to_json(snapshot)
    original_state = json.dumps(snapshot.state, separators=(",", ":"))
    nested_state = '{"deep":' * 1100 + "0" + "}" * 1100
    source = source.replace('"state":' + original_state, '"state":' + nested_state)
    with pytest.raises(EventLogError, match="nesting depth"):
        snapshot_from_json(source)
