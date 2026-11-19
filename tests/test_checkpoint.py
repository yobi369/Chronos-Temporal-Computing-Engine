# ruff: noqa: E701, E702, E501
import json
import pytest
from chronos.checkpoint import CheckpointError,CheckpointStore

def test_checkpoint_roundtrip_and_generation(tmp_path):
    store=CheckpointStore(tmp_path)
    digest=store.save({"state":{"n":4},"events":[]},generation=7)
    generation,payload=store.recover()
    assert generation==7 and payload["state"]["n"]==4 and len(digest)==64
def test_checkpoint_detects_corruption(tmp_path):
    store=CheckpointStore(tmp_path); store.save({"n":1},generation=1)
    path=tmp_path/"checkpoint-00000000000000000001.json"
    envelope=json.loads(path.read_text()); envelope["payload"]["n"]=2
    path.write_text(json.dumps(envelope))
    with pytest.raises(CheckpointError,match="checksum"): store.recover()
def test_checkpoint_missing_pointer_and_size_limit(tmp_path):
    with pytest.raises(CheckpointError): CheckpointStore(tmp_path).recover()
    with pytest.raises(CheckpointError,match="size"): CheckpointStore(tmp_path,max_bytes=2).save({"a":1},generation=1)
