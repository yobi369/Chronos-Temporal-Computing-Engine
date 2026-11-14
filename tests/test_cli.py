import json
import pytest
import subprocess
import sys

from chronos import (
    EventInput,
    SimulationEngine,
    Timeline,
    capture_timeline_continuation,
    write_timeline_continuation,
    write_event_log,
)
from chronos.cli import main
from chronos.event_log import EventLog, EventLogError


def _build_event_log(tmp_path):
    engine = SimulationEngine("cli-event-log")

    def increment(event, simulation):
        simulation.state["total"] = simulation.state.get("total", 0) + event.payload["amount"]

    engine.register("increment", increment)
    inputs = (EventInput(1, "increment", {"amount": 7}),)
    for item in inputs:
        engine.schedule(item.time, item.event_type, item.payload)
    engine.run()
    path = tmp_path / "event-log.json"
    write_event_log(path, EventLog.capture(engine, inputs))
    return path


def _build_continuation(tmp_path):
    def increment(event, simulation):
        simulation.state["total"] = simulation.state.get("total", 0) + event.payload["amount"]

    parent_engine = SimulationEngine("cli-parent")
    parent_engine.state = {"total": 3}
    parent = Timeline.capture("cli-checkpoint", parent_engine)
    branch = parent.fork("cli-branch", handlers={"increment": increment})
    inputs = (EventInput(2, "increment", {"amount": 5}),)
    branch.schedule(inputs[0].time, inputs[0].event_type, inputs[0].payload)
    branch.run()
    record = capture_timeline_continuation(parent, branch, inputs)
    path = tmp_path / "continuation.json"
    write_timeline_continuation(path, record)
    return path


def test_inspect_event_log_emits_machine_readable_metadata_without_payload_values(
    tmp_path, capsys
):
    path = _build_event_log(tmp_path)

    assert main(["inspect-event-log", str(path), "--json"]) == 0
    output = capsys.readouterr()
    summary = json.loads(output.out)

    assert summary["artifact_type"] == "event_log"
    assert summary["schema_version"] == 3
    assert summary["timeline_id"] == "cli-event-log"
    assert summary["initial_input_count"] == 1
    assert summary["recorded_event_count"] == 1
    assert summary["recorded_event_type_counts"] == {"increment": 1}
    assert "amount" not in output.out


def test_inspect_continuation_reports_branch_and_queue_metadata(tmp_path, capsys):
    path = _build_continuation(tmp_path)

    assert main(["inspect-continuation", str(path), "--json"]) == 0
    summary = json.loads(capsys.readouterr().out)

    assert summary["artifact_type"] == "timeline_continuation"
    assert summary["parent_timeline_id"] == "cli-parent"
    assert summary["timeline_id"] == "cli-branch"
    assert summary["branch_input_count"] == 1
    assert summary["recorded_event_count"] == 1
    assert summary["pending_event_count"] == 0
    assert summary["checkpoint_state_fields"] == ["total"]


def test_cli_reports_malformed_artifacts_with_nonzero_exit(tmp_path, capsys):
    path = tmp_path / "broken.json"
    path.write_text('{"schema_version":', encoding="utf-8")

    assert main(["inspect-event-log", str(path)]) == 2
    output = capsys.readouterr()
    assert "chronos:" in output.err
    assert output.out == ""


def test_module_version_command():
    completed = subprocess.run(
        [sys.executable, "-m", "chronos", "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert completed.stdout.strip() == "chronos 0.5.0"


def test_cli_reports_invalid_continuation_with_nonzero_exit(tmp_path, capsys):
    path = tmp_path / "broken-continuation.json"
    path.write_text('{"schema_version": 2}', encoding="utf-8")

    assert main(["inspect-continuation", str(path), "--json"]) == 2
    output = capsys.readouterr()
    assert "chronos:" in output.err
    assert output.out == ""


def test_create_and_verify_portable_report_with_both_artifact_types(tmp_path, capsys):
    event_log = _build_event_log(tmp_path)
    continuation = _build_continuation(tmp_path)
    report_dir = tmp_path / "customer-review"

    assert main([
        "create-report",
        "--output-dir", str(report_dir),
        "--event-log", str(event_log),
        "--continuation", str(continuation),
    ]) == 0
    created = capsys.readouterr()
    assert "Artifacts included: 2" in created.out

    report = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
    assert report["format"] == "chronos-experiment-report"
    assert len(report["artifacts"]) == 2
    assert all((report_dir / item["file"]).is_file() for item in report["artifacts"])
    assert "amount" not in json.dumps(report)

    assert main(["verify-report", str(report_dir), "--json"]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["verified"] is True
    assert verified["artifact_count"] == 2
    assert verified["event_log_count"] == 1
    assert verified["continuation_count"] == 1


def test_report_verification_detects_artifact_tampering(tmp_path, capsys):
    event_log = _build_event_log(tmp_path)
    report_dir = tmp_path / "tamper-check"
    assert main([
        "create-report", "--output-dir", str(report_dir),
        "--event-log", str(event_log),
    ]) == 0
    capsys.readouterr()

    artifact = next((report_dir / "artifacts").iterdir())
    artifact.write_text("{}\n", encoding="utf-8")
    assert main(["verify-report", str(report_dir)]) == 2
    assert "SHA-256 digest mismatch" in capsys.readouterr().err


def test_report_creation_refuses_to_overwrite_existing_directory(tmp_path, capsys):
    event_log = _build_event_log(tmp_path)
    report_dir = tmp_path / "existing"
    report_dir.mkdir()

    assert main([
        "create-report", "--output-dir", str(report_dir),
        "--event-log", str(event_log),
    ]) == 2
    assert "already exists" in capsys.readouterr().err


def _write_ed25519_keys(tmp_path, name="reviewer"):
    crypto = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    from cryptography.hazmat.primitives import serialization

    private = crypto.Ed25519PrivateKey.generate()
    private_path = tmp_path / f"{name}-private.pem"
    public_path = tmp_path / f"{name}-public.pem"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path


def test_signed_report_is_valid_but_untrusted_without_trust_input(tmp_path, capsys):
    event_log = _build_event_log(tmp_path)
    private_key, _ = _write_ed25519_keys(tmp_path)
    report_dir = tmp_path / "signed-untrusted"
    assert main([
        "create-report", "--output-dir", str(report_dir),
        "--event-log", str(event_log), "--signing-key", str(private_key),
    ]) == 0
    capsys.readouterr()

    assert (report_dir / "signature.json").is_file()
    assert private_key.read_bytes() not in (report_dir / "signature.json").read_bytes()
    assert main(["verify-report", str(report_dir), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["integrity_verified"] is True
    assert result["signature_valid"] is True
    assert result["trust_status"] == "untrusted"


def test_report_trust_requires_exact_matching_public_key(tmp_path, capsys):
    event_log = _build_event_log(tmp_path)
    private_key, public_key = _write_ed25519_keys(tmp_path, "right")
    _, wrong_public_key = _write_ed25519_keys(tmp_path, "wrong")
    report_dir = tmp_path / "signed-trusted"
    assert main([
        "create-report", "--output-dir", str(report_dir),
        "--event-log", str(event_log), "--signing-key", str(private_key),
    ]) == 0
    capsys.readouterr()

    assert main([
        "verify-report", str(report_dir),
        "--trusted-public-key", str(wrong_public_key), "--json",
    ]) == 0
    wrong = json.loads(capsys.readouterr().out)
    assert wrong["signature_valid"] is True
    assert wrong["trust_status"] == "untrusted"

    assert main([
        "verify-report", str(report_dir),
        "--trusted-public-key", str(public_key), "--json",
    ]) == 0
    trusted = json.loads(capsys.readouterr().out)
    assert trusted["signature_valid"] is True
    assert trusted["trust_status"] == "trusted"


def test_signed_report_detects_manifest_tampering(tmp_path, capsys):
    event_log = _build_event_log(tmp_path)
    private_key, _ = _write_ed25519_keys(tmp_path)
    report_dir = tmp_path / "signed-tamper"
    assert main([
        "create-report", "--output-dir", str(report_dir),
        "--event-log", str(event_log), "--signing-key", str(private_key),
    ]) == 0
    capsys.readouterr()

    manifest = report_dir / "report.json"
    manifest.write_bytes(manifest.read_bytes() + b" ")
    assert main(["verify-report", str(report_dir)]) == 2
    assert "manifest SHA-256 digest mismatch" in capsys.readouterr().err


def test_signature_envelope_rejects_unknown_fields(tmp_path, capsys):
    event_log = _build_event_log(tmp_path)
    private_key, _ = _write_ed25519_keys(tmp_path)
    report_dir = tmp_path / "signed-envelope"
    assert main([
        "create-report", "--output-dir", str(report_dir),
        "--event-log", str(event_log), "--signing-key", str(private_key),
    ]) == 0
    capsys.readouterr()

    envelope_path = report_dir / "signature.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope["unexpected"] = True
    envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
    assert main(["verify-report", str(report_dir)]) == 2
    assert "missing or unknown fields" in capsys.readouterr().err


def test_unsigned_report_remains_compatible(tmp_path, capsys):
    event_log = _build_event_log(tmp_path)
    report_dir = tmp_path / "legacy-unsigned"
    assert main([
        "create-report", "--output-dir", str(report_dir),
        "--event-log", str(event_log),
    ]) == 0
    capsys.readouterr()

    assert main(["verify-report", str(report_dir), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["integrity_verified"] is True
    assert result["signature_valid"] is False
    assert result["trust_status"] == "unsigned"


def test_render_report_creates_offline_html_after_verification(tmp_path, capsys):
    event_log = _build_event_log(tmp_path)
    report_dir = tmp_path / "review"
    assert main([
        "create-report", "--output-dir", str(report_dir),
        "--event-log", str(event_log),
    ]) == 0
    capsys.readouterr()

    assert main(["render-report", str(report_dir)]) == 0
    output = capsys.readouterr()
    rendered = report_dir / "index.html"
    document = rendered.read_text(encoding="utf-8")
    assert rendered.is_file()
    assert "Integrity and schema checks: PASS" in document
    assert "Unsigned report" in document
    assert "Artifact 1: event_log" in document
    assert "does not load remote scripts" in document
    assert "<script" not in document
    assert "Rendered reviewer report:" in output.out


def test_render_report_escapes_untrusted_filenames(tmp_path):
    original = _build_event_log(tmp_path)
    hostile = tmp_path / '<img src=x onerror="alert(1)">.json'
    hostile.write_bytes(original.read_bytes())
    report_dir = tmp_path / "escaped-review"
    from chronos.cli import create_experiment_report

    create_experiment_report(report_dir, event_logs=[hostile])
    from chronos.cli import render_experiment_report

    output = render_experiment_report(report_dir).read_text(encoding="utf-8")
    assert '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;.json' in output
    assert '<img src=x onerror="alert(1)">' not in output
    assert "<script" not in output


def test_render_report_refuses_tampered_bundle_without_writing_html(tmp_path):
    event_log = _build_event_log(tmp_path)
    report_dir = tmp_path / "tampered-render"
    from chronos.cli import create_experiment_report, render_experiment_report

    create_experiment_report(report_dir, event_logs=[event_log])
    artifact = next((report_dir / "artifacts").iterdir())
    artifact.write_text("{}\n", encoding="utf-8")

    with pytest.raises(EventLogError, match="SHA-256 digest mismatch"):
        render_experiment_report(report_dir)
    assert not (report_dir / "index.html").exists()
