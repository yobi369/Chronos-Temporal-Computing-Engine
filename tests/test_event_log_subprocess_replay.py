import subprocess
import sys

from chronos.engine import SimulationEngine
from chronos.event_log import EventInput, EventLog, event_log_to_json


def accumulate(event, simulation):
    simulation.state["total"] = simulation.state.get("total", 0) + event.payload["delta"]


def test_event_log_replays_in_fresh_python_process(tmp_path):
    engine = SimulationEngine("fresh-process-replay")
    engine.state = {"total": 7}
    engine.register("accumulate", accumulate)
    inputs = (
        EventInput(1, "accumulate", {"delta": 4}),
        EventInput(1, "accumulate", {"delta": -1}),
        EventInput(3, "accumulate", {"delta": 9}),
    )
    for item in inputs:
        engine.schedule(item.time, item.event_type, item.payload)
    engine.run()

    log = EventLog.capture(engine, inputs)
    assert log.initial_state == {"total": 7}
    path = tmp_path / "portable-history.json"
    path.write_text(event_log_to_json(log), encoding="utf-8")

    script = r"""
import sys
from pathlib import Path
from chronos.event_log import event_log_from_json, replay_event_log, state_digest

def accumulate(event, simulation):
    simulation.state["total"] = simulation.state.get("total", 0) + event.payload["delta"]

log = event_log_from_json(Path(sys.argv[1]).read_text(encoding="utf-8"))
replayed = replay_event_log(log, {"accumulate": accumulate})
print(state_digest(replayed.state))
print(len(replayed.history))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )

    output = completed.stdout.splitlines()
    assert output == [log.final_state_digest, str(len(engine.history))]
