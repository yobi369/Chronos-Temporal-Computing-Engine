import json

from chronos.event_log import EventLog, event_log_to_json, state_digest


def test_golden_canonical_event_log_serialization():
    empty_state_digest = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    log = EventLog(
        timeline_id="golden",
        initial_events=(),
        events=(),
        final_state_digest=empty_state_digest,
    )
    expected = (
        '{"events":[],"final_state_digest":"'
        + empty_state_digest
        + '","initial_events":[],"payload_schemas":{},'
        '"schema_version":2,"timeline_id":"golden"}'
    )
    assert event_log_to_json(log) == expected
    assert json.loads(expected)["schema_version"] == 2


def test_golden_state_digest_fixture_is_stable():
    state = {"alpha": 1, "nested": {"ok": True}, "z": "chronos"}
    assert state_digest(state) == (
        "7da0adb1ed88e288ca87f15cacb608abfc3c42972a01adb870e73cbb80112813"
    )
