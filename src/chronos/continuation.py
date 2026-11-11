"""Versioned, self-contained replay records for completed timeline forks."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chronos.engine import EngineSnapshot, EventHandler, SimulationEngine
from chronos.event_log import (
    DEFAULT_MAX_LOG_BYTES,
    EventInput,
    EventLog,
    EventLogError,
    ReplayMismatchError,
    _canonical_json,
    _event_to_dict,
    _input_to_dict,
    _reject_constant,
    _reject_duplicate_keys,
    _require_int,
    _require_object,
    _require_payload,
    event_log_to_json,
    state_digest,
)
from chronos.events import Event
from chronos.snapshot_io import snapshot_from_json, snapshot_to_json
from chronos.timeline import Timeline, _fork_snapshot

CONTINUATION_SCHEMA_VERSION = 1
DEFAULT_MAX_CONTINUATION_BYTES = DEFAULT_MAX_LOG_BYTES


class TimelineContinuationError(EventLogError):
    """Raised for invalid or unsupported timeline continuation records."""


@dataclass(frozen=True, slots=True)
class TimelineContinuation:
    """Portable record of a completed fork from one exact parent checkpoint."""

    parent_timeline_id: str
    timeline_id: str
    checkpoint: EngineSnapshot
    parent_history_length: int
    branch_inputs: tuple[EventInput, ...]
    events: tuple[Event, ...]
    parent_checkpoint_digest: str
    parent_history_digest: str
    parent_state_digest: str
    final_state_digest: str
    final_snapshot_digest: str
    schema_version: int = CONTINUATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "checkpoint", copy.deepcopy(self.checkpoint))
        object.__setattr__(self, "branch_inputs", copy.deepcopy(tuple(self.branch_inputs)))
        object.__setattr__(self, "events", copy.deepcopy(tuple(self.events)))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _valid_digest(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TimelineContinuationError(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def _validated_snapshot_json(snapshot: EngineSnapshot) -> str:
    encoded = snapshot_to_json(snapshot)
    snapshot_from_json(encoded)
    return encoded


def _snapshot_digest(snapshot: EngineSnapshot) -> str:
    return _sha256_text(_validated_snapshot_json(snapshot))


def _history_digest(events: tuple[Event, ...]) -> str:
    return _sha256_text(_canonical_json([_event_to_dict(event) for event in events]))


def _validate_continuation(record: TimelineContinuation) -> None:
    if type(record.schema_version) is not int or record.schema_version != CONTINUATION_SCHEMA_VERSION:
        raise TimelineContinuationError(
            f"unsupported timeline-continuation schema version: {record.schema_version}"
        )
    if not isinstance(record.parent_timeline_id, str) or not record.parent_timeline_id:
        raise TimelineContinuationError("parent_timeline_id must be non-empty")
    if not isinstance(record.timeline_id, str) or not record.timeline_id:
        raise TimelineContinuationError("timeline_id must be non-empty")
    if record.timeline_id == record.parent_timeline_id:
        raise TimelineContinuationError("a continuation must identify a distinct fork timeline")
    if not isinstance(record.checkpoint, EngineSnapshot):
        raise TimelineContinuationError("checkpoint must be an EngineSnapshot")
    if record.checkpoint.timeline_id != record.parent_timeline_id:
        raise TimelineContinuationError("checkpoint does not belong to the declared parent timeline")
    if type(record.parent_history_length) is not int or record.parent_history_length < 0:
        raise TimelineContinuationError("parent_history_length must be a non-negative integer")
    if record.parent_history_length != len(record.checkpoint.history):
        raise TimelineContinuationError("parent_history_length does not match checkpoint history")

    checkpoint_digest = _valid_digest(
        record.parent_checkpoint_digest, "parent_checkpoint_digest"
    )
    history_digest = _valid_digest(record.parent_history_digest, "parent_history_digest")
    parent_state_digest = _valid_digest(record.parent_state_digest, "parent_state_digest")
    final_state_digest = _valid_digest(record.final_state_digest, "final_state_digest")
    _valid_digest(record.final_snapshot_digest, "final_snapshot_digest")

    if _snapshot_digest(record.checkpoint) != checkpoint_digest:
        raise TimelineContinuationError("parent checkpoint digest does not match checkpoint")
    if _history_digest(record.checkpoint.history) != history_digest:
        raise TimelineContinuationError("parent history digest does not match checkpoint history")
    if state_digest(record.checkpoint.state) != parent_state_digest:
        raise TimelineContinuationError("parent state digest does not match checkpoint state")
    if not isinstance(record.branch_inputs, tuple) or not isinstance(record.events, tuple):
        raise TimelineContinuationError("branch_inputs and events must be tuples")

    # Reuse the event-log validator for canonical payload, ordering, identity,
    # and causal-parent checks across inherited and branch-local history.
    validation_log = EventLog(
        timeline_id=record.timeline_id,
        initial_events=record.branch_inputs,
        events=(*record.checkpoint.history, *record.events),
        final_state_digest=final_state_digest,
        initial_state=record.checkpoint.state,
    )
    event_log_to_json(validation_log)


def capture_timeline_continuation(
    parent: Timeline,
    branch: SimulationEngine,
    branch_inputs: Iterable[EventInput],
) -> TimelineContinuation:
    """Capture a completed fork and the exact inputs added to that branch.

    Partial runs, remaining pending events, external pre-dispatch state changes,
    and manual logical-time advancement are rejected: they are not represented
    by the recorded branch inputs.
    """
    checkpoint = copy.deepcopy(parent.snapshot)
    if not isinstance(checkpoint, EngineSnapshot):
        raise TimelineContinuationError("parent timeline has an invalid checkpoint")
    if not isinstance(branch.timeline_id, str) or not branch.timeline_id:
        raise TimelineContinuationError("branch timeline_id must be non-empty")
    if branch.timeline_id == checkpoint.timeline_id:
        raise TimelineContinuationError("branch timeline_id must differ from parent timeline_id")

    branch_snapshot = branch.snapshot()
    if branch_snapshot.history[: len(checkpoint.history)] != checkpoint.history:
        raise TimelineContinuationError("branch history does not preserve parent checkpoint history")
    if branch.initial_state != checkpoint.state:
        raise TimelineContinuationError("branch initial state differs from parent checkpoint state")
    if branch_snapshot.queue:
        raise TimelineContinuationError(
            "cannot capture an incomplete continuation while pending events remain"
        )

    expected_time = max(
        checkpoint.current_time,
        max((event.time for event in branch_snapshot.history), default=checkpoint.current_time),
    )
    if branch_snapshot.current_time != expected_time:
        raise TimelineContinuationError(
            "cannot capture a continuation after manual or non-event logical-time advancement"
        )

    inputs = tuple(copy.deepcopy(tuple(branch_inputs)))
    observed_suffix = tuple(
        copy.deepcopy(branch_snapshot.history[len(checkpoint.history) :])
    )
    record = TimelineContinuation(
        parent_timeline_id=checkpoint.timeline_id,
        timeline_id=branch.timeline_id,
        checkpoint=checkpoint,
        parent_history_length=len(checkpoint.history),
        branch_inputs=inputs,
        events=observed_suffix,
        parent_checkpoint_digest=_snapshot_digest(checkpoint),
        parent_history_digest=_history_digest(checkpoint.history),
        parent_state_digest=state_digest(checkpoint.state),
        final_state_digest=state_digest(branch_snapshot.state),
        final_snapshot_digest=_snapshot_digest(branch_snapshot),
    )
    _validate_continuation(record)
    return record


def timeline_continuation_to_json(record: TimelineContinuation) -> str:
    """Serialize a continuation using canonical JSON and a strict independent schema."""
    _validate_continuation(record)
    document = {
        "schema_version": record.schema_version,
        "parent_timeline_id": record.parent_timeline_id,
        "timeline_id": record.timeline_id,
        "checkpoint": json.loads(_validated_snapshot_json(record.checkpoint)),
        "parent_history_length": record.parent_history_length,
        "branch_inputs": [_input_to_dict(item) for item in record.branch_inputs],
        "events": [_event_to_dict(event) for event in record.events],
        "parent_checkpoint_digest": record.parent_checkpoint_digest,
        "parent_history_digest": record.parent_history_digest,
        "parent_state_digest": record.parent_state_digest,
        "final_state_digest": record.final_state_digest,
        "final_snapshot_digest": record.final_snapshot_digest,
    }
    return _canonical_json(document)


def _parse_input(raw: Any, index: int) -> EventInput:
    label = f"branch_inputs[{index}]"
    item = _require_object(
        raw, {"time", "event_type", "payload", "parent_event_id"}, label
    )
    event_type = item["event_type"]
    parent = item["parent_event_id"]
    if not isinstance(event_type, str) or not event_type:
        raise TimelineContinuationError(f"{label}.event_type must be non-empty")
    if parent is not None and (not isinstance(parent, str) or not parent):
        raise TimelineContinuationError(f"{label}.parent_event_id must be non-empty or null")
    try:
        return EventInput(
            _require_int(item["time"], f"{label}.time"),
            event_type,
            _require_payload(item["payload"], f"{label}.payload"),
            parent,
        )
    except ValueError as exc:
        raise TimelineContinuationError(str(exc)) from exc


def _parse_event(raw: Any, index: int) -> Event:
    label = f"events[{index}]"
    item = _require_object(
        raw,
        {"event_id", "time", "sequence", "event_type", "payload", "parent_event_id"},
        label,
    )
    event_id = item["event_id"]
    event_type = item["event_type"]
    parent = item["parent_event_id"]
    if not isinstance(event_id, str) or not event_id:
        raise TimelineContinuationError(f"{label}.event_id must be non-empty")
    if not isinstance(event_type, str) or not event_type:
        raise TimelineContinuationError(f"{label}.event_type must be non-empty")
    if parent is not None and (not isinstance(parent, str) or not parent):
        raise TimelineContinuationError(f"{label}.parent_event_id must be non-empty or null")
    try:
        return Event(
            event_id=event_id,
            time=_require_int(item["time"], f"{label}.time"),
            sequence=_require_int(item["sequence"], f"{label}.sequence"),
            event_type=event_type,
            payload=_require_payload(item["payload"], f"{label}.payload"),
            parent_event_id=parent,
        )
    except ValueError as exc:
        raise TimelineContinuationError(str(exc)) from exc


def timeline_continuation_from_json(source: str) -> TimelineContinuation:
    """Parse and validate timeline-continuation schema version 1."""
    try:
        document = json.loads(
            source,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except RecursionError as exc:
        raise TimelineContinuationError(
            "timeline-continuation JSON exceeds the supported nesting depth"
        ) from exc
    except json.JSONDecodeError as exc:
        raise TimelineContinuationError(
            f"invalid timeline-continuation JSON: {exc}"
        ) from exc

    expected = {
        "schema_version",
        "parent_timeline_id",
        "timeline_id",
        "checkpoint",
        "parent_history_length",
        "branch_inputs",
        "events",
        "parent_checkpoint_digest",
        "parent_history_digest",
        "parent_state_digest",
        "final_state_digest",
        "final_snapshot_digest",
    }
    document = _require_object(document, expected, "timeline continuation")
    version = _require_int(document["schema_version"], "schema_version")
    if version != CONTINUATION_SCHEMA_VERSION:
        raise TimelineContinuationError(
            f"unsupported timeline-continuation schema version: {version}"
        )
    checkpoint_document = document["checkpoint"]
    if not isinstance(checkpoint_document, dict):
        raise TimelineContinuationError("checkpoint must be a snapshot object")
    checkpoint = snapshot_from_json(_canonical_json(checkpoint_document))

    raw_inputs = document["branch_inputs"]
    raw_events = document["events"]
    if not isinstance(raw_inputs, list) or not isinstance(raw_events, list):
        raise TimelineContinuationError("branch_inputs and events must be arrays")

    record = TimelineContinuation(
        parent_timeline_id=document["parent_timeline_id"],
        timeline_id=document["timeline_id"],
        checkpoint=checkpoint,
        parent_history_length=_require_int(
            document["parent_history_length"], "parent_history_length"
        ),
        branch_inputs=tuple(_parse_input(item, index) for index, item in enumerate(raw_inputs)),
        events=tuple(_parse_event(item, index) for index, item in enumerate(raw_events)),
        parent_checkpoint_digest=document["parent_checkpoint_digest"],
        parent_history_digest=document["parent_history_digest"],
        parent_state_digest=document["parent_state_digest"],
        final_state_digest=document["final_state_digest"],
        final_snapshot_digest=document["final_snapshot_digest"],
        schema_version=version,
    )
    _validate_continuation(record)
    return record


def write_timeline_continuation(
    path: str | Path, record: TimelineContinuation
) -> None:
    """Atomically persist a canonical continuation record to a local file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = (timeline_continuation_to_json(record) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as temporary:
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


def read_timeline_continuation(
    path: str | Path, *, max_bytes: int = DEFAULT_MAX_CONTINUATION_BYTES
) -> TimelineContinuation:
    """Read a size-bounded continuation record and validate its UTF-8 JSON."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    with Path(path).open("rb") as source:
        content = source.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise TimelineContinuationError(
            f"timeline continuation exceeds the {max_bytes}-byte read limit"
        )
    try:
        return timeline_continuation_from_json(content.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise TimelineContinuationError(
            "timeline continuation must be UTF-8 encoded"
        ) from exc


def replay_timeline_continuation(
    record: TimelineContinuation,
    handlers: dict[str, EventHandler],
    *,
    max_events: int = 100_000,
) -> SimulationEngine:
    """Recreate a fork from its parent checkpoint and verify its complete result."""
    if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 0:
        raise ValueError("max_events must be a non-negative integer")
    _validate_continuation(record)
    if len(record.events) > max_events:
        raise TimelineContinuationError(
            "recorded continuation exceeds the replay event limit"
        )

    branch_snapshot = _fork_snapshot(record.checkpoint, record.timeline_id)
    engine = SimulationEngine.from_snapshot(branch_snapshot, handlers)
    for item in record.branch_inputs:
        engine.schedule(
            item.time,
            item.event_type,
            item.payload,
            parent_event_id=item.parent_event_id,
        )
    engine.run(max_events=min(max_events, len(record.events) + 1))

    if engine.pending_events:
        raise ReplayMismatchError("continuation replay left pending events")
    expected_history = (*record.checkpoint.history, *record.events)
    if engine.history != expected_history:
        raise ReplayMismatchError(
            "replayed continuation history differs from the recorded history"
        )
    if state_digest(engine.state) != record.final_state_digest:
        raise ReplayMismatchError(
            "replayed continuation state digest differs from the recorded digest"
        )
    if _snapshot_digest(engine.snapshot()) != record.final_snapshot_digest:
        raise ReplayMismatchError(
            "replayed continuation snapshot digest differs from the recorded digest"
        )
    return engine
