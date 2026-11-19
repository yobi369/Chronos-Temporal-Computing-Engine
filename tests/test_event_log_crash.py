import subprocess
import sys
import time

import pytest


@pytest.mark.parametrize("stage", ["fsync", "replace"])
def test_process_termination_before_commit_preserves_previous_log(tmp_path, stage):
    target = tmp_path / "history.json"
    marker = tmp_path / "reached-boundary"
    gate = tmp_path / "continue"
    target.write_text("previous committed history", encoding="utf-8")
    script = r"""
import sys
import time
from pathlib import Path
import chronos.event_log as event_log_module
from chronos.event_log import EventLog

target = Path(sys.argv[1])
marker = Path(sys.argv[2])
gate = Path(sys.argv[3])
stage = sys.argv[4]

def pause_at_boundary(*args):
    marker.write_text("ready", encoding="utf-8")
    while not gate.exists():
        time.sleep(0.01)

if stage == "fsync":
    event_log_module.os.fsync = pause_at_boundary
else:
    event_log_module.os.replace = pause_at_boundary

empty_state_digest = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
event_log_module.write_event_log(
    target,
    EventLog("crash-test", (), (), empty_state_digest),
)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(target), str(marker), str(gate), stage],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 10
    try:
        while not marker.exists() and time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(f"writer exited before boundary: {stdout}\n{stderr}")
            time.sleep(0.02)
        assert marker.exists(), "writer did not reach the requested persistence boundary"
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)

    assert target.read_text(encoding="utf-8") == "previous committed history"
    # A terminated process cannot execute Python cleanup; remove any orphaned
    # temporary file after confirming the previous committed generation survived.
    for temporary in tmp_path.glob(".history.json.*.tmp"):
        temporary.unlink()
