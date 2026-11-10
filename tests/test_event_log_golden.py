import json

from chronos.event_log import (
    EventLog,
    PayloadSchema,
    event_log_from_json,
    event_log_to_json,
    state_digest,
)


EMPTY_STATE_DIGEST = (
    "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
)


def test_golden_schema_v1_serialization_remains_stable():
    log = EventLog(
        timeline_id="golden",
        initial_events=(),
        events=(),
        final_state_digest=EMPTY_STATE_DIGEST,
        schema_version=1,
    )
    expected = (
        '{"events":[],"final_state_digest":"'
        + EMPTY_STATE_DIGEST
        + '","initial_events":[],"schema_version":1,"timeline_id":"golden"}'
    )

    assert event_log_to_json(log) == expected
    parsed = event_log_from_json(expected)
    assert parsed == log
    assert event_log_to_json(parsed) == expected


def test_golden_schema_v2_serialization_preserves_payload_contracts():
    log = EventLog(
        timeline_id="golden",
        initial_events=(),
        events=(),
        final_state_digest=EMPTY_STATE_DIGEST,
        schema_version=2,
        payload_schemas={
            "credit": PayloadSchema(
                required={"amount": "integer"},
                optional={"memo": "string"},
            )
        },
    )
    expected = (
        '{"events":[],"final_state_digest":"'
        + EMPTY_STATE_DIGEST
        + '","initial_events":[],"payload_schemas":{"credit":'
        '{"allow_additional_properties":false,"optional":{"memo":"string"},'
        '"required":{"amount":"integer"}}},"schema_version":2,"timeline_id":"golden"}'
    )

    assert event_log_to_json(log) == expected
    parsed = event_log_from_json(expected)
    assert parsed == log
    assert event_log_to_json(parsed) == expected


def test_golden_schema_v3_serialization_includes_initial_state():
    log = EventLog(
        timeline_id="golden",
        initial_events=(),
        events=(),
        final_state_digest=EMPTY_STATE_DIGEST,
        schema_version=3,
    )
    expected = (
        '{"events":[],"final_state_digest":"'
        + EMPTY_STATE_DIGEST
        + '","initial_events":[],"initial_state":{},"payload_schemas":{},'
        '"schema_version":3,"timeline_id":"golden"}'
    )

    assert event_log_to_json(log) == expected
    parsed = event_log_from_json(expected)
    assert parsed == log
    assert event_log_to_json(parsed) == expected


def test_golden_state_digest_fixture_is_stable():
    state = {"alpha": 1, "nested": {"ok": True}, "z": "chronos"}
    assert state_digest(state) == (
        "7da0adb1ed88e288ca87f15cacb608abfc3c42972a01adb870e73cbb80112813"
    )
