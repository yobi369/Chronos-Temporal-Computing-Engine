"""Canonical event-log serialization, persistence, and deterministic replay."""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from chronos.engine import SimulationEngine
from chronos.events import Event
from chronos.validation import validate_event_log

SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = frozenset({LEGACY_SCHEMA_VERSION, SCHEMA_VERSION})
DEFAULT_MAX_LOG_BYTES = 16 * 1024 * 1024
PAYLOAD_TYPES = frozenset({"array", "boolean", "integer", "null", "number", "object", "string"})


class EventLogError(ValueError):
    """Base error for invalid, unsupported, or unreplayable event logs."""


class ReplayMismatchError(EventLogError):
    """Raised when replay does not reproduce the recorded execution."""


@dataclass(frozen=True, slots=True)
class PayloadSchema:
    """Small, dependency-free object schema for one event type's payload."""

    required: Mapping[str, str] = field(default_factory=dict)
    optional: Mapping[str, str] = field(default_factory=dict)
    allow_additional_properties: bool = False

    def __post_init__(self) -> None:
        for label, properties in (("required", self.required), ("optional", self.optional)):
            if not isinstance(properties, Mapping):
                raise ValueError(f"{label} payload properties must be a mapping")
            for name, value_type in properties.items():
                if not isinstance(name, str) or not name:
                    raise ValueError("payload property names must be non-empty strings")
                if not isinstance(value_type, str) or value_type not in PAYLOAD_TYPES:
                    raise ValueError(
                        f"unsupported payload type for {name!r}: {value_type!r}"
                    )
        if set(self.required) & set(self.optional):
            raise ValueError("payload properties cannot be both required and optional")
        if type(self.allow_additional_properties) is not bool:
            raise ValueError("allow_additional_properties must be a boolean")
        object.__setattr__(
            self, "required", MappingProxyType(dict(sorted(self.required.items())))
        )
        object.__setattr__(
            self, "optional", MappingProxyType(dict(sorted(self.optional.items())))
        )


@dataclass(frozen=True, slots=True)
class EventInput:
    """A caller-supplied event used to start a recorded simulation."""

    time: int
    event_type: str
    payload: dict[str, Any]
    parent_event_id: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.time, bool) or not isinstance(self.time, int) or self.time < 0:
            raise ValueError("input event time must be a non-negative integer")
        if not isinstance(self.event_type, str) or not self.event_type:
            raise ValueError("input event type must not be empty")
        if not isinstance(self.payload, dict):
            raise ValueError("input event payload must be an object")
        if self.parent_event_id is not None and (
            not isinstance(self.parent_event_id, str) or not self.parent_event_id
        ):
            raise ValueError("input parent_event_id must be a non-empty string or null")


@dataclass(frozen=True, slots=True)
class EventLog:
    """Versioned replay fixture containing inputs and expected observations."""

    timeline_id: str
    initial_events: tuple[EventInput, ...]
    events: tuple[Event, ...]
    final_state_digest: str
    schema_version: int = SCHEMA_VERSION
    payload_schemas: Mapping[str, PayloadSchema] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.payload_schemas, Mapping):
            object.__setattr__(
                self, "payload_schemas", MappingProxyType(dict(self.payload_schemas))
            )

    @classmethod
    def capture(
        cls,
        engine: SimulationEngine,
        initial_events: Iterable[EventInput],
        *,
        payload_schemas: Mapping[str, PayloadSchema] | None = None,
    ) -> EventLog:
        """Capture a completed engine run, explicit inputs, and optional payload contracts."""
        return cls(
            timeline_id=engine.timeline_id,
            initial_events=tuple(initial_events),
            events=engine.history,
            final_state_digest=state_digest(engine.state),
            payload_schemas=dict(payload_schemas or {}),
        )


def _validate_json_value(value: Any, path: str = "$") -> None:
    """Reject Python values that JSON would silently coerce or serialize ambiguously."""
    if value is None or type(value) in (bool, int):
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise EventLogError(f"{path} contains text that is not valid UTF-8") from exc
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise EventLogError(f"{path} contains a non-finite number")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if not isinstance(key, str):
                raise EventLogError(f"{path} contains a non-string object key")
            _validate_json_value(key, f"{path}.<key>")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise EventLogError(
        f"{path} is not canonical JSON data: unsupported {type(value).__name__}"
    )


def _canonical_json(value: Any) -> str:
    """Encode Chronos canonical JSON: UTF-8 text, sorted keys, compact separators, finite values."""
    try:
        _validate_json_value(value)
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except RecursionError as exc:
        raise EventLogError("value exceeds the supported JSON nesting depth") from exc
    except (TypeError, ValueError) as exc:
        raise EventLogError(f"value is not canonical JSON data: {exc}") from exc


def state_digest(state: dict[str, Any]) -> str:
    """Return SHA-256 over canonical JSON state; rejects non-object or non-JSON values."""
    if not isinstance(state, dict) or any(not isinstance(key, str) for key in state):
        raise EventLogError("state must be a JSON object with string keys")
    encoded = _canonical_json(state).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _event_to_dict(event: Event) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "time": event.time,
        "sequence": event.sequence,
        "event_type": event.event_type,
        "payload": event.payload,
        "parent_event_id": event.parent_event_id,
    }


def _input_to_dict(event: EventInput) -> dict[str, Any]:
    return {
        "time": event.time,
        "event_type": event.event_type,
        "payload": event.payload,
        "parent_event_id": event.parent_event_id,
    }


def _payload_schema_to_dict(schema: PayloadSchema) -> dict[str, Any]:
    return {
        "required": dict(schema.required),
        "optional": dict(schema.optional),
        "allow_additional_properties": schema.allow_additional_properties,
    }


def _payload_matches_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return type(value) is bool
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return type(value) is list
    if expected == "object":
        return type(value) is dict and all(isinstance(key, str) for key in value)
    return False


def _validate_payload(
    event_type: str,
    payload: dict[str, Any],
    schemas: Mapping[str, PayloadSchema],
    label: str,
) -> None:
    if not isinstance(payload, dict) or any(not isinstance(key, str) for key in payload):
        raise EventLogError(f"{label} payload must be an object with string keys")
    _canonical_json(payload)
    if not schemas:
        return
    schema = schemas.get(event_type)
    if schema is None:
        raise EventLogError(f"{label} has no payload schema for event type {event_type!r}")
    declared = set(schema.required) | set(schema.optional)
    missing = set(schema.required) - set(payload)
    extra = set(payload) - declared
    if missing:
        raise EventLogError(f"{label} payload is missing required properties: {sorted(missing)}")
    if extra and not schema.allow_additional_properties:
        raise EventLogError(f"{label} payload has undeclared properties: {sorted(extra)}")
    for name, expected in (*schema.required.items(), *schema.optional.items()):
        if name in payload and not _payload_matches_type(payload[name], expected):
            raise EventLogError(
                f"{label} payload property {name!r} must be {expected}"
            )


def _validate_log(log: EventLog) -> None:
    if type(log.schema_version) is not int or log.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise EventLogError(f"unsupported event-log schema version: {log.schema_version}")
    if not isinstance(log.timeline_id, str) or not log.timeline_id:
        raise EventLogError("timeline_id must be a non-empty string")
    digest = log.final_state_digest
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise EventLogError("final_state_digest must be a lowercase SHA-256 hex digest")
    if not isinstance(log.initial_events, tuple) or not isinstance(log.events, tuple):
        raise EventLogError("initial_events and events must be tuples")
    for index, item in enumerate(log.initial_events):
        if not isinstance(item, EventInput):
            raise EventLogError(f"initial_events[{index}] must be an EventInput")
        if (
            isinstance(item.time, bool) or not isinstance(item.time, int) or item.time < 0
            or not isinstance(item.event_type, str) or not item.event_type
            or not isinstance(item.payload, dict)
            or (item.parent_event_id is not None
                and (not isinstance(item.parent_event_id, str) or not item.parent_event_id))
        ):
            raise EventLogError(f"initial_events[{index}] has invalid fields")
    for index, event in enumerate(log.events):
        if not isinstance(event, Event):
            raise EventLogError(f"events[{index}] must be an Event")
        if (
            not isinstance(event.event_id, str) or not event.event_id
            or isinstance(event.time, bool) or not isinstance(event.time, int) or event.time < 0
            or isinstance(event.sequence, bool) or not isinstance(event.sequence, int) or event.sequence < 0
            or not isinstance(event.event_type, str) or not event.event_type
            or not isinstance(event.payload, dict)
            or (event.parent_event_id is not None
                and (not isinstance(event.parent_event_id, str) or not event.parent_event_id))
        ):
            raise EventLogError(f"events[{index}] has invalid fields")
    if validate_event_log(log.events):
        raise EventLogError("event log contains inconsistent execution history")
    if not isinstance(log.payload_schemas, Mapping):
        raise EventLogError("payload_schemas must be a mapping")
    for event_type, schema in log.payload_schemas.items():
        if not isinstance(event_type, str) or not event_type:
            raise EventLogError("payload schema event types must be non-empty strings")
        if not isinstance(schema, PayloadSchema):
            raise EventLogError(f"payload schema for {event_type!r} is invalid")
        try:
            PayloadSchema(
                required=schema.required,
                optional=schema.optional,
                allow_additional_properties=schema.allow_additional_properties,
            )
        except ValueError as exc:
            raise EventLogError(str(exc)) from exc
    if log.schema_version == LEGACY_SCHEMA_VERSION and log.payload_schemas:
        raise EventLogError("schema version 1 cannot contain payload schemas")
    for index, item in enumerate(log.initial_events):
        _validate_payload(
            item.event_type, item.payload, log.payload_schemas, f"initial_events[{index}]"
        )
    for index, event in enumerate(log.events):
        _validate_payload(
            event.event_type, event.payload, log.payload_schemas, f"events[{index}]"
        )


def event_log_to_json(log: EventLog) -> str:
    """Serialize an event log using stable key ordering and compact JSON."""
    _validate_log(log)
    document: dict[str, Any] = {
        "schema_version": log.schema_version,
        "timeline_id": log.timeline_id,
        "initial_events": [_input_to_dict(item) for item in log.initial_events],
        "events": [_event_to_dict(item) for item in log.events],
        "final_state_digest": log.final_state_digest,
    }
    if log.schema_version == SCHEMA_VERSION:
        document["payload_schemas"] = {
            event_type: _payload_schema_to_dict(schema)
            for event_type, schema in sorted(log.payload_schemas.items())
        }
    return _canonical_json(document)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EventLogError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> Any:
    raise EventLogError(f"non-standard JSON numeric constant is not allowed: {token}")


def _require_object(value: Any, expected_keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise EventLogError(f"{label} must be an object with exactly {sorted(expected_keys)}")
    return value


def _require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EventLogError(f"{label} must be an integer")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise EventLogError(f"{label} must be a boolean")
    return value


def _require_field_types(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise EventLogError(f"{label} must be an object")
    result: dict[str, str] = {}
    for name, value_type in value.items():
        if not isinstance(name, str) or not name:
            raise EventLogError(f"{label} property names must be non-empty strings")
        if not isinstance(value_type, str) or value_type not in PAYLOAD_TYPES:
            raise EventLogError(f"{label}.{name} has an unsupported payload type")
        result[name] = value_type
    return result


def _require_payload(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise EventLogError(f"{label} must be an object with string keys")
    _canonical_json(value)
    return value


def _parse_payload_schemas(value: Any) -> dict[str, PayloadSchema]:
    if not isinstance(value, dict):
        raise EventLogError("payload_schemas must be an object")
    schemas: dict[str, PayloadSchema] = {}
    for event_type, raw_schema in value.items():
        if not isinstance(event_type, str) or not event_type:
            raise EventLogError("payload schema event types must be non-empty strings")
        schema = _require_object(
            raw_schema,
            {"required", "optional", "allow_additional_properties"},
            f"payload_schemas[{event_type!r}]",
        )
        try:
            schemas[event_type] = PayloadSchema(
                required=_require_field_types(
                    schema["required"], f"payload_schemas[{event_type!r}].required"
                ),
                optional=_require_field_types(
                    schema["optional"], f"payload_schemas[{event_type!r}].optional"
                ),
                allow_additional_properties=_require_bool(
                    schema["allow_additional_properties"],
                    f"payload_schemas[{event_type!r}].allow_additional_properties",
                ),
            )
        except ValueError as exc:
            raise EventLogError(str(exc)) from exc
    return schemas


def event_log_from_json(source: str) -> EventLog:
    """Parse and strictly validate event-log schema versions 1 and 2."""
    try:
        document = json.loads(
            source,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except RecursionError as exc:
        raise EventLogError("event-log JSON exceeds the supported nesting depth") from exc
    except json.JSONDecodeError as exc:
        raise EventLogError(f"invalid event-log JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise EventLogError("event log must be a JSON object")
    version = _require_int(document.get("schema_version"), "schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise EventLogError(f"unsupported event-log schema version: {version}")
    expected_keys = {
        "schema_version",
        "timeline_id",
        "initial_events",
        "events",
        "final_state_digest",
    }
    if version == SCHEMA_VERSION:
        expected_keys.add("payload_schemas")
    document = _require_object(document, expected_keys, "event log")

    timeline_id = document["timeline_id"]
    digest = document["final_state_digest"]
    if not isinstance(timeline_id, str) or not timeline_id:
        raise EventLogError("timeline_id must be a non-empty string")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise EventLogError("final_state_digest must be a lowercase SHA-256 hex digest")

    raw_inputs = document["initial_events"]
    raw_events = document["events"]
    if not isinstance(raw_inputs, list) or not isinstance(raw_events, list):
        raise EventLogError("initial_events and events must be arrays")
    schemas = (
        _parse_payload_schemas(document["payload_schemas"])
        if version == SCHEMA_VERSION
        else {}
    )

    inputs: list[EventInput] = []
    for index, raw in enumerate(raw_inputs):
        item = _require_object(
            raw,
            {"time", "event_type", "payload", "parent_event_id"},
            f"initial_events[{index}]",
        )
        time = _require_int(item["time"], f"initial_events[{index}].time")
        event_type = item["event_type"]
        parent = item["parent_event_id"]
        if not isinstance(event_type, str) or not event_type:
            raise EventLogError(f"initial_events[{index}].event_type must be non-empty")
        if parent is not None and (not isinstance(parent, str) or not parent):
            raise EventLogError(
                f"initial_events[{index}].parent_event_id must be a non-empty string or null"
            )
        try:
            inputs.append(
                EventInput(
                    time,
                    event_type,
                    _require_payload(item["payload"], f"initial_events[{index}].payload"),
                    parent,
                )
            )
        except ValueError as exc:
            raise EventLogError(str(exc)) from exc

    events: list[Event] = []
    for index, raw in enumerate(raw_events):
        item = _require_object(
            raw,
            {"event_id", "time", "sequence", "event_type", "payload", "parent_event_id"},
            f"events[{index}]",
        )
        event_id = item["event_id"]
        event_type = item["event_type"]
        parent = item["parent_event_id"]
        if not isinstance(event_id, str) or not event_id:
            raise EventLogError(f"events[{index}].event_id must be non-empty")
        if not isinstance(event_type, str) or not event_type:
            raise EventLogError(f"events[{index}].event_type must be non-empty")
        if parent is not None and (not isinstance(parent, str) or not parent):
            raise EventLogError(
                f"events[{index}].parent_event_id must be a non-empty string or null"
            )
        try:
            events.append(
                Event(
                    event_id=event_id,
                    time=_require_int(item["time"], f"events[{index}].time"),
                    sequence=_require_int(item["sequence"], f"events[{index}].sequence"),
                    event_type=event_type,
                    payload=_require_payload(item["payload"], f"events[{index}].payload"),
                    parent_event_id=parent,
                )
            )
        except ValueError as exc:
            raise EventLogError(str(exc)) from exc

    log = EventLog(timeline_id, tuple(inputs), tuple(events), digest, version, schemas)
    _validate_log(log)
    return log


def write_event_log(path: str | Path, log: EventLog) -> None:
    """Atomically persist a canonical event log to a local file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = (event_log_to_json(log) + "\n").encode("utf-8")
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(file_descriptor, "wb") as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, destination)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def read_event_log(
    path: str | Path, *, max_bytes: int = DEFAULT_MAX_LOG_BYTES
) -> EventLog:
    """Read a bounded event log; reject oversized files before parsing."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    with Path(path).open("rb") as source:
        content = source.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise EventLogError(f"event log exceeds the {max_bytes}-byte read limit")
    try:
        return event_log_from_json(content.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise EventLogError("event log must be UTF-8 encoded") from exc


def replay_event_log(
    log: EventLog, handlers: dict[str, Any], *, max_events: int = 100_000
) -> SimulationEngine:
    """Re-execute explicit inputs and verify history plus final state digest."""
    if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 0:
        raise ValueError("max_events must be a non-negative integer")
    _validate_log(log)
    if len(log.events) > max_events:
        raise EventLogError("recorded history exceeds the replay event limit")
    engine = SimulationEngine(log.timeline_id)
    for event_type, handler in handlers.items():
        engine.register(event_type, handler)
    for item in log.initial_events:
        engine.schedule(
            item.time,
            item.event_type,
            item.payload,
            parent_event_id=item.parent_event_id,
        )
    engine.run(max_events=min(max_events, len(log.events) + 1))
    if engine.pending_events:
        raise ReplayMismatchError("replay exceeded the recorded event history")
    if engine.history != log.events:
        raise ReplayMismatchError("replayed event history differs from the recorded history")
    if state_digest(engine.state) != log.final_state_digest:
        raise ReplayMismatchError("replayed final state digest differs from the recorded digest")
    return engine
