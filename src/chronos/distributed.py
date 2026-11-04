"""Deterministic merge of distributed event batches with causal validation.

This module defines an ingestion/reconciliation protocol, not a network transport,
consensus algorithm, or exactly-once execution guarantee.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Iterable
from chronos.events import Event

class CausalReconciliationError(ValueError):
    pass

@dataclass(frozen=True,slots=True)
class DistributedEvent:
    origin: str
    event: Event
    lamport: int
    def __post_init__(self) -> None:
        if not self.origin or self.lamport<0: raise ValueError("origin and non-negative Lamport time are required")

def reconcile_events(batches: Iterable[Iterable[DistributedEvent]], *,
    known_event_ids: frozenset[str]=frozenset()) -> tuple[DistributedEvent,...]:
    """Deduplicate identical event IDs, reject conflicting duplicates and topologically order."""
    by_id: dict[str,DistributedEvent]={}
    for batch in batches:
        for item in batch:
            previous=by_id.get(item.event.event_id)
            if previous is not None and previous!=item:
                raise CausalReconciliationError(f"conflicting duplicate event id: {item.event.event_id}")
            by_id[item.event.event_id]=item
    available=set(by_id)|set(known_event_ids)
    for item in by_id.values():
        parent=item.event.parent_event_id
        if parent is not None and parent not in available:
            raise CausalReconciliationError(f"missing causal parent: {parent}")
        if parent==item.event.event_id:
            raise CausalReconciliationError("event cannot be its own causal parent")
    pending=dict(by_id); emitted=set(known_event_ids); ordered=[]
    while pending:
        ready=[item for item in pending.values() if item.event.parent_event_id is None or item.event.parent_event_id in emitted]
        if not ready: raise CausalReconciliationError("causal cycle or unresolved parent dependency")
        ready.sort(key=lambda x:(x.lamport,x.origin,x.event.time,x.event.sequence,x.event.event_id))
        for item in ready:
            ordered.append(item); emitted.add(item.event.event_id); pending.pop(item.event.event_id)
    return tuple(ordered)
