"""Reproducible counterfactual supply-resilience experiment.

Run from the repository root:
    python examples/institutional_resilience_experiment.py

This illustrative discrete-event model is not a calibrated supply-chain forecast.
"""
from __future__ import annotations

from chronos import (
    EventInput,
    SimulationEngine,
    Timeline,
    capture_timeline_continuation,
    replay_timeline_continuation,
    state_digest,
    timeline_continuation_from_json,
    timeline_continuation_to_json,
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


def run_scenario(checkpoint, timeline_id, shipment_units):
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
    replayed = replay_timeline_continuation(restored_record, handlers())

    if replayed.snapshot() != branch.snapshot():
        raise AssertionError(f"{timeline_id}: replayed snapshot differs from original")

    return {
        "timeline_id": timeline_id,
        "shipment_units": shipment_units,
        "state": dict(branch.state),
        "state_digest": state_digest(branch.state),
        "continuation_json": encoded,
        "replayed_state": dict(replayed.state),
    }


def main():
    checkpoint = build_checkpoint()
    baseline_state = checkpoint.snapshot.state
    scenarios = (
        run_scenario(checkpoint, "normal-supply", shipment_units=40),
        run_scenario(checkpoint, "disrupted-supply", shipment_units=10),
    )

    print("Checkpoint state:", baseline_state)
    for scenario in scenarios:
        print(f"\n{scenario['timeline_id']}:")
        print("  shipment units:", scenario["shipment_units"])
        print("  resulting state:", scenario["state"])
        print("  state SHA-256:", scenario["state_digest"])
        print("  continuation bytes:", len(scenario["continuation_json"].encode("utf-8")))
        print("  replay verified:", scenario["replayed_state"] == scenario["state"])

    normal = scenarios[0]["state"]
    disrupted = scenarios[1]["state"]
    print("\nCounterfactual difference:")
    print("  additional shortage under disruption:", disrupted["shortage"] - normal["shortage"])


if __name__ == "__main__":
    main()
