from chronos.continuation import (
    capture_timeline_continuation,
    replay_timeline_continuation,
    timeline_continuation_to_json,
)
from chronos.engine import SimulationEngine
from chronos.event_log import (
    EventInput,
    EventLog,
    event_log_to_json,
    replay_event_log,
)
from chronos.events import Event
from chronos.snapshot_io import snapshot_to_json
from chronos.timeline import Timeline


def _apply(event, simulation):
    payload = event.payload
    simulation.state["total"] = simulation.state.get("total", 0) + payload["amount"]
    simulation.state["metadata"]["tags"].append(payload["tag"])
    if payload.get("spawn"):
        simulation.schedule(
            event.time + 1,
            "apply",
            {"amount": 3, "tag": "spawned", "nested": {"values": [3]}},
        )


def test_event_and_input_payloads_are_detached_on_construction_and_read():
    source = {"nested": {"values": [1]}}
    event = Event("event-1", 1, 0, "apply", source)
    event_input = EventInput(1, "apply", source)

    source["nested"]["values"].append(2)
    event_view = event.payload
    input_view = event_input.payload
    event_view["nested"]["values"].append(3)
    input_view["nested"]["values"].append(4)

    assert event.payload == {"nested": {"values": [1]}}
    assert event_input.payload == {"nested": {"values": [1]}}


def test_event_log_reads_cannot_mutate_captured_payloads_or_initial_state():
    engine = SimulationEngine("record-ownership")
    engine.state = {"total": 10, "metadata": {"tags": ["initial"]}}
    engine.register("apply", _apply)
    inputs = (
        EventInput(
            1,
            "apply",
            {
                "amount": 2,
                "tag": "input",
                "spawn": True,
                "nested": {"values": [1]},
            },
        ),
    )
    engine.schedule(inputs[0].time, inputs[0].event_type, inputs[0].payload)
    engine.run()

    record = EventLog.capture(engine, inputs)
    encoded_before = event_log_to_json(record)

    input_payload = record.initial_events[0].payload
    event_payload = record.events[0].payload
    initial_state = record.initial_state
    input_payload["nested"]["values"].append(2)
    event_payload["nested"]["values"].append(3)
    initial_state["metadata"]["tags"].append("mutated")

    assert event_log_to_json(record) == encoded_before
    replayed = replay_event_log(record, {"apply": _apply})
    assert replayed.history == engine.history
    assert replayed.state == engine.state


def test_snapshot_reads_cannot_mutate_state_or_event_payloads():
    engine = SimulationEngine("snapshot-ownership")
    engine.state = {"total": 0, "metadata": {"tags": []}}
    engine.register("apply", _apply)
    engine.schedule(
        1,
        "apply",
        {"amount": 1, "tag": "first", "nested": {"values": [1]}},
    )
    engine.schedule(
        2,
        "apply",
        {"amount": 2, "tag": "second", "nested": {"values": [2]}},
    )
    engine.step()

    snapshot = engine.snapshot()
    encoded_before = snapshot_to_json(snapshot)

    state_view = snapshot.state
    history_payload = snapshot.history[0].payload
    pending_payload = snapshot.queue[0].payload
    state_view["metadata"]["tags"].append("mutated")
    history_payload["nested"]["values"].append(3)
    pending_payload["nested"]["values"].append(4)

    assert snapshot_to_json(snapshot) == encoded_before
    restored = SimulationEngine.from_snapshot(snapshot, {"apply": _apply})
    assert restored.snapshot() == snapshot


def test_continuation_reads_cannot_mutate_checkpoint_inputs_history_or_queue():
    parent_engine = SimulationEngine("root")
    parent_engine.state = {"total": 0, "metadata": {"tags": ["root"]}}
    parent_engine.register("apply", _apply)
    parent_engine.schedule(
        1,
        "apply",
        {"amount": 1, "tag": "parent", "nested": {"values": [1]}},
    )
    parent_engine.run()
    parent_engine.schedule(
        2,
        "apply",
        {"amount": 2, "tag": "inherited", "nested": {"values": [2]}},
    )

    parent = Timeline.capture("checkpoint", parent_engine)
    branch = parent.fork("branch", handlers={"apply": _apply})
    branch_input = EventInput(
        3,
        "apply",
        {"amount": 3, "tag": "branch", "nested": {"values": [3]}},
    )
    branch.schedule(branch_input.time, branch_input.event_type, branch_input.payload)
    branch.run(max_events=1)

    record = capture_timeline_continuation(parent, branch, (branch_input,))
    encoded_before = timeline_continuation_to_json(record)

    checkpoint_state = record.checkpoint.state
    input_payload = record.branch_inputs[0].payload
    history_payload = record.events[0].payload
    pending_payload = record.pending_events[0].payload
    checkpoint_state["metadata"]["tags"].append("mutated")
    input_payload["nested"]["values"].append(4)
    history_payload["nested"]["values"].append(5)
    pending_payload["nested"]["values"].append(6)

    assert timeline_continuation_to_json(record) == encoded_before
    replayed = replay_timeline_continuation(record, {"apply": _apply})
    assert replayed.snapshot() == branch.snapshot()
