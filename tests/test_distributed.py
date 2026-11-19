# ruff: noqa: E701, E702, E501
import pytest
from chronos.distributed import CausalReconciliationError,DistributedEvent,reconcile_events
from chronos.events import Event

def item(id,seq,parent=None,origin="node-a",lamport=1):
    return DistributedEvent(origin,Event(id,seq,seq,"tick",{},parent),lamport)
def test_merge_is_deterministic_deduplicated_and_causally_ordered():
    root=item("a:0",0,origin="a",lamport=1); child=item("b:0",1,"a:0",origin="b",lamport=2)
    merged=reconcile_events(([child],[root,child]))
    assert [x.event.event_id for x in merged]==["a:0","b:0"]
def test_merge_rejects_conflicts_missing_parent_and_cycle():
    with pytest.raises(CausalReconciliationError,match="conflicting"):
        reconcile_events(([item("x",0),item("x",1)],))
    with pytest.raises(CausalReconciliationError,match="missing"):
        reconcile_events(([item("x",0,"absent")],))
    with pytest.raises(CausalReconciliationError,match="cycle"):
        reconcile_events(([item("x",0,"y"),item("y",1,"x")],))
