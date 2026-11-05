"""Versioned snapshot serialization and migration."""
from __future__ import annotations
import json
from typing import Any
from chronos.engine import EngineSnapshot
from chronos.event_log import EventLogError, _canonical_json, _event_to_dict, _require_int, state_digest
from chronos.events import Event
from chronos.validation import validate_event_log

SNAPSHOT_SCHEMA_VERSION = 2
SNAPSHOT_FORMAT = "chronos.engine-snapshot"

def _event_from_dict(raw: Any, label: str) -> Event:
    keys = {"event_id", "time", "sequence", "event_type", "payload", "parent_event_id"}
    if not isinstance(raw, dict) or set(raw) != keys:
        raise EventLogError(f"{label} has an invalid event structure")
    if not isinstance(raw["event_id"], str) or not raw["event_id"]:
        raise EventLogError(f"{label}.event_id must be non-empty")
    if not isinstance(raw["event_type"], str) or not raw["event_type"]:
        raise EventLogError(f"{label}.event_type must be non-empty")
    payload = raw["payload"]
    if not isinstance(payload, dict):
        raise EventLogError(f"{label}.payload must be an object")
    state_digest(payload)
    parent = raw["parent_event_id"]
    if parent is not None and not isinstance(parent, str):
        raise EventLogError(f"{label}.parent_event_id must be a string or null")
    return Event(raw["event_id"], _require_int(raw["time"], f"{label}.time"),
        _require_int(raw["sequence"], f"{label}.sequence"), raw["event_type"], payload, parent)

def _engine_dict(snapshot: EngineSnapshot) -> dict[str, Any]:
    return {"timeline_id": snapshot.timeline_id, "current_time": snapshot.current_time,
        "next_sequence": snapshot.next_sequence, "queue": [_event_to_dict(e) for e in snapshot.queue],
        "history": [_event_to_dict(e) for e in snapshot.history], "state": snapshot.state,
        "logical_clock_value": snapshot.logical_clock_value}

def migrate_v1_to_v2(document: dict[str, Any]) -> dict[str, Any]:
    """Migrate the legacy flat v1 envelope to the v2 envelope."""
    expected = {"schema_version", "timeline_id", "current_time", "next_sequence",
        "queue", "history", "state", "logical_clock_value"}
    if set(document) != expected or document.get("schema_version") != 1:
        raise EventLogError("invalid version-1 snapshot document")
    engine = {key: value for key, value in document.items() if key != "schema_version"}
    return {"format": SNAPSHOT_FORMAT, "schema_version": 2,
        "metadata": {"writer": "chronos", "migration": "v1-to-v2"}, "engine": engine}

def _decode_engine(raw: Any) -> EngineSnapshot:
    keys = {"timeline_id", "current_time", "next_sequence", "queue",
        "history", "state", "logical_clock_value"}
    if not isinstance(raw, dict) or set(raw) != keys:
        raise EventLogError("snapshot engine payload has an invalid structure")
    if not isinstance(raw["timeline_id"], str) or not raw["timeline_id"]:
        raise EventLogError("timeline_id must be non-empty")
    if not isinstance(raw["state"], dict) or not isinstance(raw["queue"], list) or not isinstance(raw["history"], list):
        raise EventLogError("snapshot state must be an object and queue/history arrays")
    state_digest(raw["state"])
    queue = tuple(_event_from_dict(e, f"queue[{i}]") for i, e in enumerate(raw["queue"]))
    history = tuple(_event_from_dict(e, f"history[{i}]") for i, e in enumerate(raw["history"]))
    current = _require_int(raw["current_time"], "current_time")
    next_sequence = _require_int(raw["next_sequence"], "next_sequence")
    clock = _require_int(raw["logical_clock_value"], "logical_clock_value")
    if min(current, next_sequence, clock) < 0:
        raise EventLogError("snapshot counters must be non-negative")
    if any(e.time < current for e in queue):
        raise EventLogError("snapshot queue contains an event in the past")
    all_events = (*queue, *history)
    if len({e.sequence for e in all_events}) != len(all_events):
        raise EventLogError("snapshot contains duplicate event sequences")
    if len({e.event_id for e in all_events}) != len(all_events):
        raise EventLogError("snapshot contains duplicate event IDs")
    if any(e.sequence >= next_sequence for e in all_events):
        raise EventLogError("snapshot next_sequence does not exceed all event sequences")
    if validate_event_log(history):
        raise EventLogError("snapshot history is inconsistent")
    return EngineSnapshot(raw["timeline_id"], current, next_sequence, queue, history, raw["state"], clock)

def snapshot_to_json(snapshot: EngineSnapshot) -> str:
    """Serialize an engine snapshot using schema version 2."""
    return _canonical_json({"format": SNAPSHOT_FORMAT, "schema_version": 2,
        "metadata": {"writer": "chronos", "migration": None}, "engine": _engine_dict(snapshot)})

def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EventLogError(f"duplicate snapshot JSON key: {key}")
        result[key] = value
    return result

def snapshot_from_json(source: str) -> EngineSnapshot:
    """Read v2 or migrate a supported flat v1 snapshot in memory."""
    try:
        document = json.loads(source, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise EventLogError(f"invalid snapshot JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise EventLogError("snapshot document must be an object")
    version = document.get("schema_version")
    if version == 1:
        document = migrate_v1_to_v2(document)
    if document.get("schema_version") != 2:
        raise EventLogError(f"unsupported snapshot schema version: {version}")
    if set(document) != {"format", "schema_version", "metadata", "engine"}:
        raise EventLogError("version-2 snapshot has unexpected or missing fields")
    if document["format"] != SNAPSHOT_FORMAT:
        raise EventLogError("snapshot format identifier is invalid")
    metadata = document["metadata"]
    if not isinstance(metadata, dict) or set(metadata) != {"writer", "migration"}:
        raise EventLogError("snapshot metadata has an invalid structure")
    if metadata["writer"] != "chronos" or metadata["migration"] not in (None, "v1-to-v2"):
        raise EventLogError("snapshot metadata values are unsupported")
    return _decode_engine(document["engine"])
