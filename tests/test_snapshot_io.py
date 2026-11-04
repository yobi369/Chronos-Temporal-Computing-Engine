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
