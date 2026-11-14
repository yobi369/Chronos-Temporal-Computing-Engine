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
from chronos.event_log import EventLog


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
    private_path, public_path = tmp_path / f"{name}-private.pem", tmp_path / f"{name}-public.pem"
    private_path.write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    public_path.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return private_path, public_path

def test_signed_report_is_valid_but_untrusted_without_trust_input(tmp_path, capsys):
    event_log=_build_event_log(tmp_path); private,_=_write_ed25519_keys(tmp_path); bundle=tmp_path/"signed"
    assert main(["create-report","--output-dir",str(bundle),"--event-log",str(event_log),"--signing-key",str(private)])==0
    capsys.readouterr()
    assert (bundle/"signature.json").is_file()
    assert private.read_bytes() not in (bundle/"signature.json").read_bytes()
    assert main(["verify-report",str(bundle),"--json"])==0
    result=json.loads(capsys.readouterr().out)
    assert result["integrity_verified"] and result["signature_valid"] and result["trust_status"]=="untrusted"

def test_report_trust_requires_exact_matching_public_key(tmp_path,capsys):
    event_log=_build_event_log(tmp_path); private,public=_write_ed25519_keys(tmp_path,"right"); _,wrong=_write_ed25519_keys(tmp_path,"wrong"); bundle=tmp_path/"signed"
    assert main(["create-report","--output-dir",str(bundle),"--event-log",str(event_log),"--signing-key",str(private)])==0
    capsys.readouterr()
    assert main(["verify-report",str(bundle),"--trusted-public-key",str(wrong),"--json"])==0
    assert json.loads(capsys.readouterr().out)["trust_status"]=="untrusted"
    assert main(["verify-report",str(bundle),"--trusted-public-key",str(public),"--json"])==0
    result=json.loads(capsys.readouterr().out)
    assert result["signature_valid"] and result["trust_status"]=="trusted"

def test_signed_report_detects_manifest_tampering(tmp_path,capsys):
    event_log=_build_event_log(tmp_path); private,_=_write_ed25519_keys(tmp_path); bundle=tmp_path/"signed"
    assert main(["create-report","--output-dir",str(bundle),"--event-log",str(event_log),"--signing-key",str(private)])==0
    capsys.readouterr(); manifest=bundle/"report.json"; manifest.write_bytes(manifest.read_bytes()+b" ")
    assert main(["verify-report",str(bundle)])==2
    assert "manifest SHA-256 digest mismatch" in capsys.readouterr().err

def test_signature_envelope_rejects_unknown_fields(tmp_path,capsys):
    event_log=_build_event_log(tmp_path); private,_=_write_ed25519_keys(tmp_path); bundle=tmp_path/"signed"
    assert main(["create-report","--output-dir",str(bundle),"--event-log",str(event_log),"--signing-key",str(private)])==0
    capsys.readouterr(); path=bundle/"signature.json"; env=json.loads(path.read_text()); env["extra"]=True; path.write_text(json.dumps(env))
    assert main(["verify-report",str(bundle)])==2
    assert "missing or unknown fields" in capsys.readouterr().err

def test_unsigned_report_compatibility(tmp_path,capsys):
    event_log=_build_event_log(tmp_path); bundle=tmp_path/"unsigned"
    assert main(["create-report","--output-dir",str(bundle),"--event-log",str(event_log)])==0
    capsys.readouterr(); assert main(["verify-report",str(bundle),"--json"])==0
    result=json.loads(capsys.readouterr().out)
    assert result["integrity_verified"] and not result["signature_valid"] and result["trust_status"]=="unsigned"
