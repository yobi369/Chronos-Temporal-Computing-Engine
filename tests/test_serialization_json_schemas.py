import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from chronos import EventLog, PayloadSchema, SimulationEngine, state_digest
from chronos.continuation import timeline_continuation_from_json
from chronos.event_log import event_log_from_json, event_log_to_json
from chronos.snapshot_io import snapshot_to_json


SCHEMAS = Path(__file__).parents[1] / "docs" / "schemas"
FIXTURES = Path(__file__).parent / "fixtures"


def _schema(name: str) -> dict[str, Any]:
    document = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(document)
    return document


def _validate(name: str, source: str) -> None:
    Draft202012Validator(_schema(name)).validate(json.loads(source))


def test_event_log_v3_schema_accepts_canonical_serialization():
    digest = state_digest({})
    log = EventLog(
        timeline_id="schema-test",
        initial_events=(),
        events=(),
        final_state_digest=digest,
        schema_version=3,
        payload_schemas={
            "credit": PayloadSchema(
                required={"amount": "integer"},
                optional={"memo": "string"},
            )
        },
        initial_state={"opening": 3},
    )

    _validate("event-log-v3.schema.json", event_log_to_json(log))


def test_snapshot_v2_schema_accepts_canonical_serialization():
    engine = SimulationEngine("schema-test")
    engine.register("noop", lambda event, simulation: None)
    engine.schedule(4, "noop", {"value": 1})

    _validate("engine-snapshot-v2.schema.json", snapshot_to_json(engine.snapshot()))


def test_timeline_continuation_v2_schema_accepts_golden_fixture():
    source = (
        FIXTURES / "timeline-continuation-v2-empty.json"
    ).read_text(encoding="utf-8").rstrip("\n")
    # Runtime parsing remains the semantic authority; JSON Schema checks the wire shape.
    timeline_continuation_from_json(source)
    _validate("timeline-continuation-v2.schema.json", source)

def test_event_log_v1_schema_accepts_canonical_legacy_serialization():
    log = EventLog(
        timeline_id="schema-test-v1",
        initial_events=(),
        events=(),
        final_state_digest=state_digest({}),
        schema_version=1,
    )
    source = event_log_to_json(log)

    assert event_log_from_json(source) == log
    _validate("event-log-v1.schema.json", source)


def test_event_log_v2_schema_accepts_canonical_payload_contract_serialization():
    log = EventLog(
        timeline_id="schema-test-v2",
        initial_events=(),
        events=(),
        final_state_digest=state_digest({}),
        schema_version=2,
        payload_schemas={
            "credit": PayloadSchema(
                required={"amount": "integer"},
                optional={"memo": "string"},
            )
        },
    )
    source = event_log_to_json(log)

    assert event_log_from_json(source) == log
    _validate("event-log-v2.schema.json", source)


def test_event_log_version_schemas_reject_incompatible_envelopes():
    logs = {
        version: event_log_to_json(
            EventLog(
                timeline_id=f"schema-test-v{version}",
                initial_events=(),
                events=(),
                final_state_digest=state_digest({}),
                schema_version=version,
                payload_schemas=(
                    {"credit": PayloadSchema(required={"amount": "integer"})}
                    if version >= 2
                    else {}
                ),
                initial_state={"opening": 5} if version == 3 else {},
            )
        )
        for version in (1, 2, 3)
    }
    documents = {version: json.loads(source) for version, source in logs.items()}
    validators = {
        version: Draft202012Validator(_schema(f"event-log-v{version}.schema.json"))
        for version in (1, 2, 3)
    }

    for version, validator in validators.items():
        assert validator.is_valid(documents[version])
        for other_version, document in documents.items():
            if other_version != version:
                assert not validator.is_valid(document)

