import json
from dataclasses import replace
from pathlib import Path

from chronos import (
    SimulationEngine,
    Timeline,
    capture_timeline_continuation,
    replay_timeline_continuation,
    timeline_continuation_from_json,
    timeline_continuation_to_json,
)


FIXTURES = Path(__file__).parent / "fixtures"


def _empty_continuation():
    parent_engine = SimulationEngine("root")
    parent = Timeline.capture("checkpoint", parent_engine)
    branch = parent.fork("branch")
    return capture_timeline_continuation(parent, branch, ())


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8").rstrip("\n")


def test_timeline_continuation_v1_canonical_json_golden_fixture():
    record = replace(_empty_continuation(), schema_version=1)
    expected = _fixture("timeline-continuation-v1-empty.json")

    assert "pending_events" not in json.loads(expected)
    assert timeline_continuation_to_json(record) == expected

    parsed = timeline_continuation_from_json(expected)
    assert parsed.schema_version == 1
    assert timeline_continuation_to_json(parsed) == expected
    replayed = replay_timeline_continuation(parsed, {})
    assert replayed.timeline_id == "branch"
    assert replayed.snapshot().state == {}


def test_timeline_continuation_v2_canonical_json_golden_fixture():
    record = _empty_continuation()
    expected = _fixture("timeline-continuation-v2-empty.json")

    assert json.loads(expected)["pending_events"] == []
    assert timeline_continuation_to_json(record) == expected

    parsed = timeline_continuation_from_json(expected)
    assert parsed.schema_version == 2
    assert timeline_continuation_to_json(parsed) == expected
    replayed = replay_timeline_continuation(parsed, {})
    assert replayed.timeline_id == "branch"
    assert replayed.snapshot().state == {}
