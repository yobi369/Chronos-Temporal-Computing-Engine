""""Reproducible counterfactual supply-resilience experiment.

Create portable continuation artifacts:
    python examples/institutional_resilience_experiment.py --output-dir chronos-artifacts

Verify those artifacts in a separate Python process:
    python examples/institutional_resilience_experiment.py --verify-artifacts chronos-artifacts

This illustrative discrete-event model is not a calibrated supply-chain forecast.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from chronos import (
    EventInput,
    SimulationEngine,
    Timeline,
    capture_timeline_continuation,
    read_timeline_continuation,
    replay_timeline_continuation,
    state_digest,
    timeline_continuation_from_json,
    timeline_continuation_to_json,
    write_timeline_continuation,
)


def receive_shipment(event, engine):
    engine.state["inventory"] += event.payload["units"]


def fulfil_demand(event, engine):
    requested = event.payload["units"]
    fulfilled = min(requested, engine.state["inventory"])
    engine.state["inventory"] -= fulfilled
    engine.state["fulfilled"] += fulfilled
    engine.state["shortage"] += requested - fulfilled


def handlers():
    return {
        "shipment_received": receive_shipment,
        "demand_arrived": fulfil_demand,
    }


def build_checkpoint():
    engine = SimulationEngine("supply-baseline")
    engine.state = {"inventory": 50, "fulfilled": 0, "shortage": 0}
    engine.register("shipment_received", receive_shipment)
    engine.register("demand_arrived", fulfil_demand)
    engine.schedule(1, "demand_arrived", {"units": 30})
    engine.run()
    return Timeline.capture("supply-baseline", engine)


def run_scenario(checkpoint, timeline_id, shipment_units, artifact_dir=None):
    branch = checkpoint.fork(timeline_id, handlers=handlers())
    inputs = (
        EventInput(2, "shipment_received", {"units": shipment_units}),
        EventInput(3, "demand_arrived", {"units": 45}),
    )
    for item in inputs:
        branch.schedule(item.time, item.event_type, item.payload)
    branch.run()

    record = capture_timeline_continuation(checkpoint, branch, inputs)
    encoded = timeline_continuation_to_json(record)
    restored_record = timeline_continuation_from_json(encoded)
    artifact_path = None
    if artifact_dir is not None:
        artifact_path = Path(artifact_dir) / f"{timeline_id}.continuation.json"
        write_timeline_continuation(artifact_path, restored_record)
        restored_record = read_timeline_continuation(artifact_path)

    replayed = replay_timeline_continuation(restored_record, handlers())
    if replayed.snapshot() != branch.snapshot():
        raise AssertionError(f"{timeline_id}: replayed snapshot differs from original")

    result = {
        "timeline_id": timeline_id,
        "shipment_units": shipment_units,
        "state": dict(branch.state),
        "state_digest": state_digest(branch.state),
        "continuation_json": encoded,
        "replayed_state": dict(replayed.state),
    }
    if artifact_path is not None:
        result["artifact_path"] = str(artifact_path)
    return result


def verify_artifacts(artifact_dir):
    expected = {
        "normal-supply": {"inventory": 15, "fulfilled": 75, "shortage": 0},
        "disrupted-supply": {"inventory": 0, "fulfilled": 60, "shortage": 15},
    }
    for timeline_id, expected_state in expected.items():
        path = Path(artifact_dir) / f"{timeline_id}.continuation.json"
        record = read_timeline_continuation(path)
        if record.timeline_id != timeline_id:
            raise AssertionError(
                f"{path}: expected timeline {timeline_id!r}, got {record.timeline_id!r}"
            )
        replayed = replay_timeline_continuation(record, handlers())
        if replayed.state != expected_state:
            raise AssertionError(
                f"{timeline_id}: expected {expected_state}, got {replayed.state}"
            )
        print(
            f"PASS {timeline_id}: fresh-process replay verified; "
            f"state={replayed.state}; SHA-256={state_digest(replayed.state)}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--output-dir",
        type=Path,
        default=Path("chronos-artifacts"),
        help="directory for portable continuation JSON files (default: chronos-artifacts)",
    )
    mode.add_argument(
        "--verify-artifacts",
        type=Path,
        help="verify previously exported continuation files in this process",
    )
    args = parser.parse_args()

    if args.verify_artifacts is not None:
        verify_artifacts(args.verify_artifacts)
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = build_checkpoint()
    baseline_state = checkpoint.snapshot.state
    scenarios = (
        run_scenario(checkpoint, "normal-supply", shipment_units=40, artifact_dir=args.output_dir),
        run_scenario(checkpoint, "disrupted-supply", shipment_units=10, artifact_dir=args.output_dir),
    )

    print("Checkpoint state:", baseline_state)
    for scenario in scenarios:
        print(f"\n{scenario['timeline_id']}:")
        print("  shipment units:", scenario["shipment_units"])
        print("  resulting state:", scenario["state"])
        print("  state SHA-256:", scenario["state_digest"])
        print("  continuation bytes:", len(scenario["continuation_json"].encode("utf-8")))
        print("  replay verified:", scenario["replayed_state"] == scenario["state"])
        print("  portable artifact:", scenario["artifact_path"])

    normal = scenarios[0]["state"]
    disrupted = scenarios[1]["state"]
    print("\nCounterfactual difference:")
    print("  additional shortage under disruption:", disrupted["shortage"] - normal["shortage"])
    print("\nNext, verify the saved artifacts in a separate process:")
    print(f"  python examples/institutional_resilience_experiment.py --verify-artifacts {args.output_dir}")


if __name__ == "__main__":
    main()
