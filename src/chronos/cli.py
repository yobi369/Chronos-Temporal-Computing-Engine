"""Chronos command-line inspection and portable experiment reports."""
from __future__ import annotations

import argparse
import hashlib
import html
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


def render_experiment_report(
    report_dir: str | Path,
    *,
    output: str | Path | None = None,
    trusted_public_key: str | Path | None = None,
) -> Path:
    """Render a verified report as a self-contained, offline HTML reviewer document."""
    root = Path(report_dir)
    verification = verify_experiment_report(
        root,
        trusted_public_key=trusted_public_key,
    )
    manifest_path = root / REPORT_FILENAME
    manifest: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
    trust_status = str(verification["trust_status"])
    if trust_status == "trusted":
        signature_label = "Signature valid · trusted key match"
    elif trust_status == "untrusted":
        signature_label = "Signature valid · signer not locally trusted"
    else:
        signature_label = "Unsigned report"

    artifact_sections: list[str] = []
    for index, artifact in enumerate(manifest["artifacts"], start=1):
        summary = json.dumps(artifact["summary"], indent=2, sort_keys=True)
        artifact_sections.append(
            "<section class=\"artifact\">"
            f"<h3>Artifact {index}: {html.escape(str(artifact.get('kind', 'unknown')))}</h3>"
            "<dl>"
            f"<dt>Original filename</dt><dd>{html.escape(str(artifact.get('original_name', 'unknown')))}</dd>"
            f"<dt>Bundle path</dt><dd><code>{html.escape(str(artifact.get('file', 'unknown')))}</code></dd>"
            f"<dt>SHA-256</dt><dd class=\"hash\">{html.escape(str(artifact.get('sha256', 'unknown')))}</dd>"
            "</dl>"
            f"<details><summary>Validated metadata</summary><pre>{html.escape(summary)}</pre></details>"
            "</section>"
        )

    version = html.escape(str(manifest.get("chronos_version", "unknown")))
    key_id = verification.get("key_id")
    key_detail = (
        f"<p class=\"muted\">Signer key ID: <code>{html.escape(str(key_id))}</code></p>"
        if key_id is not None
        else ""
    )
    trust_note = html.escape(str(verification["trust_note"]))
    scope = html.escape(str(verification["verification_scope"]))
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy"
 content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Chronos experiment review</title>
<style>
:root {{
 color-scheme: light;
 font-family: Inter, ui-sans-serif, system-ui, sans-serif;
 color: #172033;
 background: #f4f6fa;
}}
body {{ margin: 0; line-height: 1.55; }}
main {{ max-width: 960px; margin: 0 auto; padding: 42px 22px 64px; }}
header, .panel, .artifact {{
 background: #fff;
 border: 1px solid #dce2eb;
 border-radius: 14px;
 padding: 22px;
 margin: 0 0 18px;
}}
.eyebrow {{ color: #53627a; font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }}
h1 {{ margin: 8px 0; font-size: clamp(1.8rem, 5vw, 2.7rem); letter-spacing: -.04em; }}
h2 {{ margin: 0 0 14px; font-size: 1.25rem; }}
h3 {{ margin: 0 0 12px; font-size: 1.05rem; }}
p {{ margin: 8px 0; }}
.status {{
 display: inline-block;
 border-radius: 999px;
 background: #edf2f8;
 padding: 5px 11px;
 font-size: .9rem;
 font-weight: 700;
}}
dl {{ display: grid; grid-template-columns: minmax(110px, 160px) minmax(0, 1fr); gap: 7px 16px; margin: 14px 0; }}
dt {{ color: #53627a; }} dd {{ margin: 0; overflow-wrap: anywhere; }}
.hash, code, pre {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
.hash {{ overflow-wrap: anywhere; font-size: .85rem; }}
pre {{ overflow-x: auto; background: #f5f7fa; padding: 14px; border-radius: 8px; font-size: .82rem; }}
summary {{ cursor: pointer; font-weight: 650; }}
.muted {{ color: #53627a; font-size: .9rem; }}
.notice {{ border-left: 4px solid #8795aa; padding-left: 14px; }}
footer {{ color: #53627a; font-size: .85rem; padding: 8px 2px; }}
@media (max-width: 560px) {{
 main {{ padding: 20px 12px 40px; }}
 dl {{ grid-template-columns: 1fr; gap: 2px; }}
 dd {{ margin-bottom: 9px; }}
}}
</style>
</head>
<body>
<main>
<header>
<div class="eyebrow">Chronos · Portable experiment review</div>
<h1>Experiment report</h1>
<p class="muted">Chronos version {version} · {verification["artifact_count"]} bundled artifact(s)</p>
<span class="status">Integrity and schema checks: PASS</span>
</header>
<section class="panel">
<h2>Signature and trust</h2>
<p><strong>{html.escape(signature_label)}</strong></p>
{key_detail}
<p class="muted">{trust_note}</p>
</section>
<section class="panel">
<h2>Included artifacts</h2>
{''.join(artifact_sections)}
</section>
<section class="panel">
<h2>What this report verifies</h2>
<p>{scope}</p>
<p class="notice">A successful report check is not a simulation replay, scientific validation,
proof of authorship, identity, authorization, revocation status, or trusted timestamp.
A valid signature is trusted only when its public key matches the key explicitly
supplied by the reviewer.</p>
</section>
<footer>Generated locally by Chronos. This file is self-contained and does not load
remote scripts, fonts, images, or services.</footer>
</main>
</body>
</html>
"""
    destination = Path(output) if output is not None else root / "index.html"
    protected_paths = {
        manifest_path.resolve(),
        (root / "signature.json").resolve(),
        *[(root / str(item["file"])).resolve() for item in manifest["artifacts"]],
    }
    if destination.resolve() in protected_paths:
        raise EventLogError("HTML output path must not overwrite a report manifest or artifact")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(document)
        os.replace(temporary_name, destination)
    except Exception:
        try:
            Path(temporary_name).unlink()
        except FileNotFoundError:
            pass
        raise
    return destination


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

    render = commands.add_parser(
        "render-report",
        help="Render a verified report as a self-contained offline HTML document.",
    )
    render.add_argument("report_dir", type=Path)
    render.add_argument("--output", type=Path, help="HTML output path (default: REPORT_DIR/index.html).")
    render.add_argument(
        "--trusted-public-key",
        type=Path,
        help="PEM Ed25519 public key for an explicit local trust decision.",
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
        elif args.command == "render-report":
            rendered_path = render_experiment_report(
                args.report_dir,
                output=args.output,
                trusted_public_key=args.trusted_public_key,
            )
            print(f"Rendered reviewer report: {rendered_path}")
            print("Integrity and schema checks: PASS")
            rendered_verification = verify_experiment_report(
                args.report_dir,
                trusted_public_key=args.trusted_public_key,
            )
            print(f"Signature valid: {rendered_verification['signature_valid']}")
            print(f"Trust status: {rendered_verification['trust_status']}")
            return 0
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
