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


def test_incomplete_or_manually_advanced_forks_cannot_be_captured():
    parent_engine = SimulationEngine("root")
    parent_engine.state = {"total": 10}
    parent_engine.register("add", add)
    parent = Timeline.capture("checkpoint", parent_engine)

    pending = parent.fork("pending", handlers={"add": add})
    pending.schedule(2, "add", {"amount": 1})
    with pytest.raises(EventLogError, match="pending events remain"):
        capture_timeline_continuation(
            parent, pending, (EventInput(2, "add", {"amount": 1}),)
        )

    advanced = parent.fork("advanced", handlers={"add": add})
    advanced.schedule(2, "add", {"amount": 1})
    advanced.run(until=10)
    with pytest.raises(EventLogError, match="logical-time advancement"):
        capture_timeline_continuation(
            parent, advanced, (EventInput(2, "add", {"amount": 1}),)
        )
