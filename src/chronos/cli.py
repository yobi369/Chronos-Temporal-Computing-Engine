"""Chronos command-line inspection and portable experiment reports."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from chronos import __version__
from chronos.continuation import read_timeline_continuation
from chronos.event_log import DEFAULT_MAX_LOG_BYTES, EventLogError, read_event_log


REPORT_FILENAME = "report.json"
REPORT_FORMAT = "chronos-experiment-report"
REPORT_SCHEMA_VERSION = 1


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


def _inspect_artifact(kind: str, path: str | Path) -> dict[str, object]:
    if kind == "event_log":
        return inspect_event_log(path)
    if kind == "timeline_continuation":
        return inspect_continuation(path)
    raise EventLogError(f"unsupported report artifact type: {kind!r}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_experiment_report(
    output_dir: str | Path,
    *,
    event_logs: Sequence[str | Path] = (),
    continuations: Sequence[str | Path] = (),
    signing_key: str | Path | None = None,
) -> dict[str, object]:
    """Create a portable report directory containing validated copies of artifacts."""
    sources = [
        ("event_log", Path(path))
        for path in event_logs
    ] + [
        ("timeline_continuation", Path(path))
        for path in continuations
    ]
    if not sources:
        raise EventLogError("at least one event log or continuation is required")

    destination = Path(output_dir)
    if destination.exists():
        raise FileExistsError(f"report output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    try:
        artifact_dir = staging / "artifacts"
        artifact_dir.mkdir()
        entries: list[dict[str, object]] = []
        for index, (kind, source) in enumerate(sources, start=1):
            if source.stat().st_size > DEFAULT_MAX_LOG_BYTES:
                raise EventLogError(
                    f"{source}: exceeds the {DEFAULT_MAX_LOG_BYTES}-byte report artifact limit"
                )
            source_summary = _inspect_artifact(kind, source)
            filename = f"artifact-{index:03d}-{kind}.json"
            copied_path = artifact_dir / filename
            shutil.copyfile(source, copied_path)
            copied_summary = _inspect_artifact(kind, copied_path)
            if copied_summary != source_summary:
                raise EventLogError(f"{source}: changed while the report copy was being created")
            entries.append(
                {
                    "kind": kind,
                    "original_name": source.name,
                    "file": f"artifacts/{filename}",
                    "sha256": _sha256_file(copied_path),
                    "summary": copied_summary,
                }
            )

        report: dict[str, object] = {
            "format": REPORT_FORMAT,
            "schema_version": REPORT_SCHEMA_VERSION,
            "chronos_version": __version__,
            "artifacts": entries,
            "verification_note": (
                "Artifact hashes detect accidental changes; they are not signatures, "
                "proof of authorship, or authenticated audit evidence. This report "
                "validates artifact structure and metadata but does not replay simulations."
            ),
        }
        report_path = staging / REPORT_FILENAME
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if signing_key is not None:
            from chronos.signing import sign_report_manifest
            sign_report_manifest(report_path, signing_key)
        os.replace(staging, destination)
        return report
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_experiment_report(
    report_dir: str | Path,
    *,
    trusted_public_key: str | Path | None = None,
) -> dict[str, object]:
    """Validate every bundled artifact, its digest, and its recorded metadata."""
    root = Path(report_dir)
    report_path = root / REPORT_FILENAME
    try:
        document: Any = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EventLogError(f"{report_path}: invalid report JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise EventLogError("report root must be a JSON object")
    if document.get("format") != REPORT_FORMAT:
        raise EventLogError("unsupported experiment report format")
    if document.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise EventLogError("unsupported experiment report schema version")
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise EventLogError("report must contain at least one artifact")

    root_resolved = root.resolve()
    for index, entry in enumerate(artifacts):
        if not isinstance(entry, dict):
            raise EventLogError(f"report artifacts[{index}] must be an object")
        kind = entry.get("kind")
        relative_name = entry.get("file")
        expected_hash = entry.get("sha256")
        expected_summary = entry.get("summary")
        if kind not in {"event_log", "timeline_continuation"}:
            raise EventLogError(f"report artifacts[{index}] has an unsupported kind")
        if (
            not isinstance(relative_name, str)
            or "\\" in relative_name
            or PurePosixPath(relative_name).parts[:1] != ("artifacts",)
            or len(PurePosixPath(relative_name).parts) != 2
        ):
            raise EventLogError(f"report artifacts[{index}] has an unsafe artifact path")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise EventLogError(f"report artifacts[{index}] has an invalid SHA-256 digest")
        if not isinstance(expected_summary, dict):
            raise EventLogError(f"report artifacts[{index}] has no metadata summary")

        artifact_path = root / relative_name
        if not artifact_path.resolve().is_relative_to(root_resolved):
            raise EventLogError(f"report artifacts[{index}] resolves outside the report directory")
        if artifact_path.stat().st_size > DEFAULT_MAX_LOG_BYTES:
            raise EventLogError(f"{artifact_path}: exceeds the supported artifact size")
        actual_hash = _sha256_file(artifact_path)
        if actual_hash != expected_hash:
            raise EventLogError(f"{artifact_path}: SHA-256 digest mismatch")
        actual_summary = _inspect_artifact(kind, artifact_path)
        if actual_summary != expected_summary:
            raise EventLogError(f"{artifact_path}: validated metadata differs from the report")

    if (root / "signature.json").is_file():
        from chronos.signing import verify_report_signature
        signature_result = verify_report_signature(report_path, trusted_public_key_path=trusted_public_key)
    else:
        if trusted_public_key is not None:
            raise EventLogError("trusted public key supplied, but report is unsigned")
        signature_result = {
            "signature_valid": False,
            "trust_status": "unsigned",
            "key_id": None,
            "algorithm": None,
            "trust_note": "No detached signature is present.",
        }

    return {
        "verified": True,
        "integrity_verified": True,
        **signature_result,
        "artifact_count": len(artifacts),
        "event_log_count": sum(item["kind"] == "event_log" for item in artifacts),
        "continuation_count": sum(
            item["kind"] == "timeline_continuation" for item in artifacts
        ),
        "verification_scope": (
            "Artifact hashes, supported schemas, and metadata. Detached Ed25519 signatures "
            "are checked when present; trust requires an explicit matching public key. "
            "No simulation replay, identity proof, authorization, revocation, or trusted timestamp is provided."
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chronos",
        description="Inspect Chronos artifacts and create portable experiment reports.",
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

    create = commands.add_parser(
        "create-report",
        help="Create a portable report directory with validated artifact copies.",
    )
    create.add_argument("--output-dir", required=True, type=Path)
    create.add_argument("--event-log", action="append", type=Path, default=[])
    create.add_argument("--continuation", action="append", type=Path, default=[])
    create.add_argument(
        "--signing-key",
        type=Path,
        help="PEM Ed25519 private key; encrypted keys prompt for passphrase.",
    )

    verify = commands.add_parser(
        "verify-report",
        help="Verify the hashes, schemas, and metadata in a portable report directory.",
    )
    verify.add_argument("report_dir", type=Path)
    verify.add_argument(
        "--trusted-public-key",
        type=Path,
        help="PEM Ed25519 public key for an explicit local trust decision.",
    )
    verify.add_argument("--json", action="store_true", dest="json_output")

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
        elif args.command == "create-report":
            if not args.event_log and not args.continuation:
                parser.error("create-report requires at least one --event-log or --continuation")
            summary = create_experiment_report(
                args.output_dir,
                event_logs=args.event_log,
                continuations=args.continuation,
                signing_key=args.signing_key,
            )
        elif args.command == "verify-report":
            summary = verify_experiment_report(args.report_dir, trusted_public_key=args.trusted_public_key)
        else:  # pragma: no cover - argparse requires a subcommand
            parser.error("a command is required")
            return 2
    except (EventLogError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"chronos: {exc}", file=sys.stderr)
        return 2

    if args.command == "create-report":
        print(f"Created Chronos experiment report: {args.output_dir}")
        print(f"Artifacts included: {len(args.event_log) + len(args.continuation)}")
        if args.signing_key is not None:
            print("Report signature: Ed25519 detached signature created")
    elif args.command == "verify-report" and not args.json_output:
        print(f"PASS: verified {summary['artifact_count']} report artifacts")
        print(f"Signature valid: {summary['signature_valid']}")
        print(f"Trust status: {summary['trust_status']}")
        print(str(summary["verification_scope"]))
    elif getattr(args, "json_output", False):
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
