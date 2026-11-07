# ruff: noqa: E501, E701, E702
import subprocess
import sys
import pytest
from chronos.checkpoint import CheckpointStore

@pytest.mark.parametrize(("stage","expected_generation","expected_exit"),[
    ("before_generation_replace",1,70),
    ("after_generation_replace",1,73),
    ("before_pointer_replace",1,71),
    ("after_pointer_replace",2,72),
])
def test_process_termination_at_checkpoint_commit_boundaries(tmp_path,stage,expected_generation,expected_exit):
    CheckpointStore(tmp_path).save({"version":1},generation=1)
    script=r'''
import os,sys
from pathlib import Path
from chronos.checkpoint import CheckpointStore
directory=sys.argv[1]
stage=sys.argv[2]
store=CheckpointStore(directory)
if stage=="after_generation_replace":
    original=store._atomic_write
    def hooked(path,data):
        original(path,data)
        if path.name.startswith("checkpoint-00000000000000000002"):
            os._exit(73)
    store._atomic_write=hooked
else:
    original=os.replace
    def hooked(source,target):
        name=Path(target).name
        if stage=="before_generation_replace" and name.startswith("checkpoint-00000000000000000002"):
            os._exit(70)
        if stage=="before_pointer_replace" and name=="CURRENT":
            os._exit(71)
        result=original(source,target)
        if stage=="after_pointer_replace" and name=="CURRENT":
            os._exit(72)
        return result
    os.replace=hooked
store.save({"version":2},generation=2)
'''
    result=subprocess.run([sys.executable,"-c",script,str(tmp_path),stage],check=False)
    assert result.returncode==expected_exit
    generation,payload=CheckpointStore(tmp_path).recover()
    assert generation==expected_generation
    assert payload=={"version":expected_generation}
