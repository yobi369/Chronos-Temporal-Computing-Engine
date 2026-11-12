import subprocess
import sys
from dataclasses import replace

import pytest

from chronos import (
    EventInput,
    EventLogError,
    ReplayMismatchError,
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


def add(event, simulation):
    simulation.state["total"] = (
        simulation.state.get("total", 0) + event.payload["amount"]
    )


def build_continuation():
    parent_engine = SimulationEngine("root")
    parent_engine.state = {"total": 10}
    parent_engine.register("add", add)
    parent_engine.schedule(1, "add", {"amount": 2})
    parent_engine.run(max_events=1)
    parent_engine.schedule(2, "add", {"amount": 3})

    parent = Timeline.capture("checkpoint", parent_engine)
    branch = parent.fork("branch", handlers={"add": add})
    inputs = (EventInput(3, "add", {"amount": 5}),)
    for item in inputs:
        branch.schedule(item.time, item.event_type, item.payload)
    branch.run()

    record = capture_timeline_continuation(parent, branch, inputs)
    return parent, branch, record


def test_fork_continuation_persists_and_replays_exact_snapshot(tmp_path):
    parent, branch, record = build_continuation()
    encoded = timeline_continuation_to_json(record)
    parsed = timeline_continuation_from_json(encoded)

    assert timeline_continuation_to_json(parsed) == encoded
    assert parsed.parent_timeline_id == "root"
    assert parsed.timeline_id == "branch"
    assert parsed.parent_history_length == len(parent.snapshot.history)
    assert parsed.events == branch.history[len(parent.snapshot.history) :]

    path = tmp_path / "nested" / "branch-continuation.json"
    write_timeline_continuation(path, parsed)
    loaded = read_timeline_continuation(path)
    replayed = replay_timeline_continuation(loaded, {"add": add})

    assert replayed.snapshot() == branch.snapshot()
    assert replayed.history == branch.history
    assert state_digest(replayed.state) == record.final_state_digest


def test_fork_continuation_replays_in_a_fresh_python_process(tmp_path):
    _, branch, record = build_continuation()
    path = tmp_path / "branch-continuation.json"
    write_timeline_continuation(path, record)

    script = r"""
import sys
from pathlib import Path
from chronos import read_timeline_continuation, replay_timeline_continuation, state_digest

def add(event, simulation):
    simulation.state["total"] = simulation.state.get("total", 0) + event.payload["amount"]

record = read_timeline_continuation(Path(sys.argv[1]))
engine = replay_timeline_continuation(record, {"add": add})
print(state_digest(engine.state))
print(len(engine.history))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert completed.stdout.splitlines() == [
        record.final_state_digest,
        str(len(branch.history)),
    ]


def test_continuation_rejects_checkpoint_and_final_state_tampering():
    _, _, record = build_continuation()
    record.checkpoint.state["total"] = 999
    with pytest.raises(EventLogError, match="checkpoint digest"):
        timeline_continuation_to_json(record)

    _, _, intact = build_continuation()
    altered = replace(intact, final_state_digest=state_digest({"total": 999}))
    with pytest.raises(ReplayMismatchError, match="state digest"):
        replay_timeline_continuation(altered, {"add": add})


def test_continuation_rejects_branch_inputs_that_do_not_match_history():
    _, _, record = build_continuation()
    altered = replace(
        record,
        branch_inputs=(EventInput(3, "add", {"amount": 999}),),
    )
    with pytest.raises(EventLogError, match="not present unchanged"):
        timeline_continuation_to_json(altered)


def test_completed_continuation_schema_v1_remains_readable_and_writable():
    _, _, record = build_continuation()
    legacy = replace(record, schema_version=1, pending_events=())

    encoded = timeline_continuation_to_json(legacy)
    assert '"pending_events"' not in encoded
    parsed = timeline_continuation_from_json(encoded)

    assert parsed.schema_version == 1
    assert timeline_continuation_to_json(parsed) == encoded
    replayed = replay_timeline_continuation(parsed, {"add": add})
    assert replayed.history == (*record.checkpoint.history, *record.events)


def test_partial_fork_continuation_replays_with_handler_generated_pending_event(
    tmp_path,
):
    def spawn(event, simulation):
        simulation.state["spawned"] = True
        simulation.schedule(event.time + 1, "add", {"amount": 7})

    parent_engine = SimulationEngine("root")
    parent_engine.state = {"total": 10}
    parent_engine.register("add", add)
    parent_engine.schedule(1, "add", {"amount": 2})
    parent = Timeline.capture("checkpoint", parent_engine)
    parent_before = parent.snapshot

    handlers = {"add": add, "spawn": spawn}
    branch = parent.fork("branch", handlers=handlers)
    inputs = (EventInput(2, "spawn", {"flag": True}),)
    for item in inputs:
        branch.schedule(item.time, item.event_type, item.payload)
    branch.run(max_events=2)

    record = capture_timeline_continuation(parent, branch, inputs)
    assert record.schema_version == 2
    assert record.events == branch.history[len(parent.snapshot.history) :]
    assert record.pending_events == branch.pending_events
    assert len(record.pending_events) == 1
    assert record.pending_events[0].parent_event_id == branch.history[-1].event_id

    path = tmp_path / "partial-branch.json"
    write_timeline_continuation(path, record)
    loaded = read_timeline_continuation(path)
    replayed = replay_timeline_continuation(loaded, handlers)

    assert replayed.snapshot() == branch.snapshot()
    assert replayed.pending_events == branch.pending_events
    assert parent.snapshot == parent_before


def test_zero_dispatch_partial_continuation_preserves_entire_queue():
    parent_engine = SimulationEngine("root")
    parent_engine.state = {"total": 4}
    parent_engine.register("add", add)
    parent_engine.schedule(1, "add", {"amount": 2})
    parent = Timeline.capture("checkpoint", parent_engine)
    branch = parent.fork("branch", handlers={"add": add})
    inputs = (EventInput(2, "add", {"amount": 3}),)
    branch.schedule(2, "add", {"amount": 3})

    record = capture_timeline_continuation(parent, branch, inputs)
    assert record.events == ()
    assert record.pending_events == branch.pending_events

    replayed = replay_timeline_continuation(record, {"add": add}, max_events=0)
    assert replayed.snapshot() == branch.snapshot()


def test_partial_continuation_rejects_pending_queue_tampering():
    def spawn(event, simulation):
        simulation.schedule(event.time + 1, "add", {"amount": 7})

    parent_engine = SimulationEngine("root")
    parent_engine.state = {"total": 1}
    parent_engine.register("add", add)
    parent = Timeline.capture("checkpoint", parent_engine)
    branch = parent.fork("branch", handlers={"add": add, "spawn": spawn})
    inputs = (EventInput(1, "spawn", {"flag": True}),)
    branch.schedule(1, "spawn", {"flag": True})
    branch.run(max_events=1)
    record = capture_timeline_continuation(parent, branch, inputs)

    altered_event = replace(record.pending_events[0], payload={"amount": 999})
    altered = replace(record, pending_events=(altered_event,))
    with pytest.raises(ReplayMismatchError, match="pending queue"):
        replay_timeline_continuation(altered, {"add": add, "spawn": spawn})


def test_incomplete_forks_with_manual_logical_time_advance_cannot_be_captured():
    parent_engine = SimulationEngine("root")
    parent_engine.state = {"total": 10}
    parent_engine.register("add", add)
    parent = Timeline.capture("checkpoint", parent_engine)

    advanced = parent.fork("advanced", handlers={"add": add})
    advanced.schedule(2, "add", {"amount": 1})
    advanced.run(until=10)
    with pytest.raises(EventLogError, match="logical-time advancement"):
        capture_timeline_continuation(
            parent, advanced, (EventInput(2, "add", {"amount": 1}),)
        )


def test_partial_continuation_replays_and_resumes_in_a_fresh_python_process(
    tmp_path,
):
    def spawn(event, simulation):
        simulation.state["spawned"] = True
        simulation.schedule(event.time + 1, "add", {"amount": 7})

    parent_engine = SimulationEngine("root")
    parent_engine.state = {"total": 10}
    parent = Timeline.capture("checkpoint", parent_engine)
    handlers = {"add": add, "spawn": spawn}
    branch = parent.fork("branch", handlers=handlers)
    inputs = (EventInput(2, "spawn", {"flag": True}),)
    branch.schedule(inputs[0].time, inputs[0].event_type, inputs[0].payload)
    branch.run(max_events=1)

    record = capture_timeline_continuation(parent, branch, inputs)
    assert len(record.events) == 1
    assert len(record.pending_events) == 1

    path = tmp_path / "partial-fresh-process.json"
    write_timeline_continuation(path, record)

    expected = SimulationEngine.from_snapshot(branch.snapshot(), handlers)
    expected.run()

    script = r"""
import sys
from pathlib import Path
from chronos import read_timeline_continuation, replay_timeline_continuation, state_digest

def add(event, simulation):
    simulation.state["total"] = simulation.state.get("total", 0) + event.payload["amount"]

def spawn(event, simulation):
    simulation.state["spawned"] = True
    simulation.schedule(event.time + 1, "add", {"amount": 7})

record = read_timeline_continuation(Path(sys.argv[1]))
engine = replay_timeline_continuation(record, {"add": add, "spawn": spawn})
print(state_digest(engine.state))
print(len(engine.pending_events))
engine.run()
print(state_digest(engine.state))
print(len(engine.history))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert completed.stdout.splitlines() == [
        record.final_state_digest,
        str(len(record.pending_events)),
        state_digest(expected.state),
        str(len(expected.history)),
    ]
