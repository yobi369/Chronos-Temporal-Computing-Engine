import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from chronos import EventLog, PayloadSchema, SimulationEngine, state_digest
from chronos.continuation import timeline_continuation_from_json
from chronos.event_log import event_log_to_json
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
