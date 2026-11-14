from collections import defaultdict
from collections.abc import Iterable

from chronos.events import Event


class CausalGraph:
    """Directed provenance graph derived from declared event-parent links."""

    def __init__(self, events: Iterable[Event]) -> None:
        self._parents: dict[str, str | None] = {}
        self._children: dict[str, set[str]] = defaultdict(set)
        for event in events:
            if event.event_id in self._parents:
                raise ValueError(f'duplicate event id: {event.event_id}')
            parent = event.parent_event_id
            if parent is not None and parent not in self._parents:
                raise ValueError(f'unknown or forward causal parent: {parent}')
            self._parents[event.event_id] = parent
            if parent is not None:
                self._children[parent].add(event.event_id)

    @property
    def event_ids(self) -> frozenset[str]:
        return frozenset(self._parents)

    def parent_of(self, event_id: str) -> str | None:
        self._require_event(event_id)
        return self._parents[event_id]

    def ancestors(self, event_id: str) -> frozenset[str]:
        self._require_event(event_id)
        result: set[str] = set()
        parent = self._parents[event_id]
        while parent is not None:
            if parent in result:
                raise ValueError('cycle detected in causal graph')
            result.add(parent)
            parent = self._parents[parent]
        return frozenset(result)

    def descendants(self, event_id: str) -> frozenset[str]:
        self._require_event(event_id)
        result: set[str] = set()
        pending = list(self._children[event_id])
        while pending:
            child = pending.pop()
            if child not in result:
                result.add(child)
                pending.extend(self._children[child])
        return frozenset(result)

    def _require_event(self, event_id: str) -> None:
        if event_id not in self._parents:
            raise KeyError(event_id)
