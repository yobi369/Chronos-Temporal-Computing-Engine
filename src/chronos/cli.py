"""Read-only command-line inspection for persisted Chronos artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from chronos import __version__
from chronos.continuation import read_timeline_continuation
from chronos.event_log import EventLogError, read_event_log


def inspect_event_log(path: str | Path) -> dict[str, object]:
    """Read and validate an event log, returning metadata without payload values."""
    log = read_event_log(path)
    input_types = Counter(item.event_type for item in log.initial_events)
    event_types = Counter(event.event_type for event in log.events)
    payload_contracts = {
        name: {
            "required": dict(schema.required),
            "optional": dict(schema.optional),
            "allow_additional_properties": schema.allow_additional_properties,
        }
        for name, schema in sorted(log.payload_schemas.items())
    }
    return {
        "artifact_type": "event_log",
        "schema_version": log.schema_version,
        "timeline_id": log.timeline_id,
        "initial_input_count": len(log.initial_events),
        "recorded_event_count": len(log.events),
        "initial_input_type_counts": dict(sorted(input_types.items())),
        "recorded_event_type_counts": dict(sorted(event_types.items())),
        "initial_state_captured": log.schema_version >= 3,
        "initial_state_fields": sorted(log.initial_state),
        "payload_contracts": payload_contracts,
        "final_state_digest": log.final_state_digest,
        "digest_note": "SHA-256 reproducibility checksum; not a signature or authenticity proof.",
    }


def inspect_continuation(path: str | Path) -> dict[str, object]:
    """Read and validate a continuation, returning metadata without state values."""
    record = read_timeline_continuation(path)
    return {
        "artifact_type": "timeline_continuation",
        "schema_version": record.schema_version,
        "parent_timeline_id": record.parent_timeline_id,
        "timeline_id": record.timeline_id,
        "parent_history_length": record.parent_history_length,
        "branch_input_count": len(record.branch_inputs),
        "recorded_event_count": len(record.events),
        "pending_event_count": len(record.pending_events),
        "branch_input_types": sorted({item.event_type for item in record.branch_inputs}),
        "recorded_event_types": sorted({event.event_type for event in record.events}),
        "pending_event_types": sorted({event.event_type for event in record.pending_events}),
        "checkpoint_state_fields": sorted(record.checkpoint.state),
        "parent_checkpoint_digest": record.parent_checkpoint_digest,
        "parent_state_digest": record.parent_state_digest,
        "final_state_digest": record.final_state_digest,
        "final_snapshot_digest": record.final_snapshot_digest,
        "digest_note": "SHA-256 reproducibility checksums; not signatures or authenticity proofs.",
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chronos",
        description="Inspect and validate saved Chronos event logs and timeline continuations.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("inspect-event-log", "Validate and summarize a persisted event log."),
        ("inspect-continuation", "Validate and summarize a persisted timeline continuation."),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("file", type=Path, help="Path to the JSON artifact.")
        command.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Emit the summary as machine-readable JSON.",
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Chronos CLI and return a process exit status."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect-event-log":
            summary = inspect_event_log(args.file)
        elif args.command == "inspect-continuation":
            summary = inspect_continuation(args.file)
        else:  # pragma: no cover - argparse requires a subcommand
            parser.error("a command is required")
            return 2
    except (EventLogError, OSError, ValueError) as exc:
        print(f"chronos: {exc}", file=sys.stderr)
        return 2

    if args.json_output:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        artifact_label = str(summary["artifact_type"]).replace("_", " ")
        print(f"Chronos {artifact_label}")
        for key, value in summary.items():
            if key in {"artifact_type", "digest_note"}:
                continue
            label = key.replace("_", " ").capitalize()
            print(f"{label}: {value}")
        print(f"Note: {summary['digest_note']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
