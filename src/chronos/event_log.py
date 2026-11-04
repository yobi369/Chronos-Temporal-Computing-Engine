"""Canonical event-log serialization, persistence, and deterministic replay."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chronos.engine import SimulationEngine
from chronos.events import Event
from chronos.validation import validate_event_log

SCHEMA_VERSION = 1
DEFAULT_MAX_LOG_BYTES = 16 * 1024 * 1024


class EventLogError(ValueError):
    """Base error for invalid, unsupported, or unreplayable event logs."""


class ReplayMismatchError(EventLogError):
    """Raised when replay does not reproduce the recorded execution."""


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


@dataclass(frozen=True, slots=True)
class EventLog:
    """Versioned replay fixture containing inputs and expected observations."""

    timeline_id: str
    initial_events: tuple[EventInput, ...]
    events: tuple[Event, ...]
    final_state_digest: str
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def capture(
        cls, engine: SimulationEngine, initial_events: Iterable[EventInput]
    ) -> EventLog:
        """Capture a completed engine run and its explicit external inputs."""
        return cls(
            timeline_id=engine.timeline_id,
            initial_events=tuple(initial_events),
            events=engine.history,
            final_state_digest=state_digest(engine.state),
        )


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise EventLogError(f"value is not canonical JSON data: {exc}") from exc


def state_digest(state: dict[str, Any]) -> str:
    """Return SHA-256 over canonical JSON state; rejects non-JSON values."""
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


def event_log_to_json(log: EventLog) -> str:
    """Serialize an event log using stable key ordering and compact JSON."""
    if log.schema_version != SCHEMA_VERSION:
        raise EventLogError(f"unsupported event-log schema version: {log.schema_version}")
    if validate_event_log(log.events):
        raise EventLogError("event log contains inconsistent execution history")
    document = {
        "schema_version": log.schema_version,
        "timeline_id": log.timeline_id,
        "initial_events": [_input_to_dict(item) for item in log.initial_events],
        "events": [_event_to_dict(item) for item in log.events],
        "final_state_digest": log.final_state_digest,
    }
    return _canonical_json(document)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EventLogError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _require_object(value: Any, expected_keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise EventLogError(f"{label} must be an object with exactly {sorted(expected_keys)}")
    return value


def _require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EventLogError(f"{label} must be an integer")
    return value


def _require_payload(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise EventLogError(f"{label} must be an object with string keys")
    _canonical_json(value)
    return value


def event_log_from_json(source: str) -> EventLog:
    """Parse and strictly validate a version-1 event log."""
    try:
        document = json.loads(source, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise EventLogError(f"invalid event-log JSON: {exc}") from exc
    document = _require_object(
        document,
        {"schema_version", "timeline_id", "initial_events", "events", "final_state_digest"},
        "event log",
    )
    version = _require_int(document["schema_version"], "schema_version")
    if version != SCHEMA_VERSION:
        raise EventLogError(f"unsupported event-log schema version: {version}")
    timeline_id = document["timeline_id"]
    digest = document["final_state_digest"]
    if not isinstance(timeline_id, str) or not timeline_id:
        raise EventLogError("timeline_id must be a non-empty string")
    if not isinstance(digest, str) or len(digest) != 64:
        raise EventLogError("final_state_digest must be a SHA-256 hex digest")
    try:
        int(digest, 16)
    except ValueError as exc:
        raise EventLogError("final_state_digest must be hexadecimal") from exc

    raw_inputs = document["initial_events"]
    raw_events = document["events"]
    if not isinstance(raw_inputs, list) or not isinstance(raw_events, list):
        raise EventLogError("initial_events and events must be arrays")

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
        if parent is not None and not isinstance(parent, str):
            raise EventLogError(
                f"initial_events[{index}].parent_event_id must be a string or null"
            )
        try:
            inputs.append(
                EventInput(
                    time,
                    event_type,
                    _require_payload(item["payload"], "payload"),
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
        if parent is not None and not isinstance(parent, str):
            raise EventLogError(f"events[{index}].parent_event_id must be a string or null")
        try:
            events.append(
                Event(
                    event_id=event_id,
                    time=_require_int(item["time"], f"events[{index}].time"),
                    sequence=_require_int(item["sequence"], f"events[{index}].sequence"),
                    event_type=event_type,
                    payload=_require_payload(item["payload"], "payload"),
                    parent_event_id=parent,
                )
            )
        except ValueError as exc:
            raise EventLogError(str(exc)) from exc

    if validate_event_log(events):
        raise EventLogError("event log contains inconsistent execution history")
    return EventLog(timeline_id, tuple(inputs), tuple(events), digest, version)


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
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
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
    if max_events < 0:
        raise ValueError("max_events must be non-negative")
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
