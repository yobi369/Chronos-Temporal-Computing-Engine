# ruff: noqa: E501, E701, E702
import subprocess
import sys
from chronos.checkpoint import CheckpointStore

def test_process_termination_between_generation_and_pointer_keeps_previous_commit(tmp_path):
    store=CheckpointStore(tmp_path)
    store.save({"version":1},generation=1)
    script=r'''
import os,sys
from chronos.checkpoint import CheckpointStore
store=CheckpointStore(sys.argv[1])
original=store._atomic_write
def crash_after_generation(path,data):
    original(path,data)
    if path.name.startswith("checkpoint-00000000000000000002"):
        os._exit(73)
store._atomic_write=crash_after_generation
store.save({"version":2},generation=2)
'''
    result=subprocess.run([sys.executable,"-c",script,str(tmp_path)],check=False)
    assert result.returncode==73
    generation,payload=CheckpointStore(tmp_path).recover()
    assert generation==1 and payload=={"version":1}
