import subprocess
import sys
from pathlib import Path
from runpy import run_path

_EXAMPLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "institutional_resilience_experiment.py"
)
_EXAMPLE = run_path(str(_EXAMPLE_PATH))
build_checkpoint = _EXAMPLE["build_checkpoint"]
run_scenario = _EXAMPLE["run_scenario"]


def test_reference_experiment_replays_counterfactual_branches_exactly():
    checkpoint = build_checkpoint()
    checkpoint_before = checkpoint.snapshot

    normal = run_scenario(checkpoint, "normal-supply-test", shipment_units=40)
    disrupted = run_scenario(checkpoint, "disrupted-supply-test", shipment_units=10)

    assert normal["state"] == {
        "inventory": 15,
        "fulfilled": 75,
        "shortage": 0,
    }
    assert disrupted["state"] == {
        "inventory": 0,
        "fulfilled": 60,
        "shortage": 15,
    }
    assert normal["replayed_state"] == normal["state"]
    assert disrupted["replayed_state"] == disrupted["state"]
    assert checkpoint.snapshot == checkpoint_before
    assert normal["state_digest"] != disrupted["state_digest"]


def test_reference_experiment_exports_and_verifies_artifacts_in_fresh_processes(
    tmp_path,
):
    repository_root = Path(__file__).resolve().parents[1]
    created = subprocess.run(
        [
            sys.executable,
            str(_EXAMPLE_PATH),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert "normal-supply.continuation.json" in created.stdout
    assert "disrupted-supply.continuation.json" in created.stdout
    assert (tmp_path / "normal-supply.continuation.json").is_file()
    assert (tmp_path / "disrupted-supply.continuation.json").is_file()

    verified = subprocess.run(
        [
            sys.executable,
            str(_EXAMPLE_PATH),
            "--verify-artifacts",
            str(tmp_path),
        ],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert "PASS normal-supply: fresh-process replay verified" in verified.stdout
    assert "PASS disrupted-supply: fresh-process replay verified" in verified.stdout
