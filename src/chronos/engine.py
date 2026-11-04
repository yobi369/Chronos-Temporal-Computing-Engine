from __future__ import annotations

import copy
import heapq
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from chronos.clock import LogicalClock
from chronos.events import Event

EventHandler = Callable[[Event, 'SimulationEngine'], None]  # noqa: UP037


@dataclass(frozen=True, slots=True)
class EngineSnapshot:
    timeline_id: str
    current_time: int
    next_sequence: int
    queue: tuple[Event, ...]
    history: tuple[Event, ...]
    state: dict[str, Any]
    logical_clock_value: int


class SimulationEngine:
    """Single-process deterministic event scheduler ordered by (time, sequence)."""

    def __init__(self, timeline_id: str = 'root') -> None:
        self.timeline_id = timeline_id
        self.current_time = 0
        self.state: dict[str, Any] = {}
        self._queue: list[tuple[int, int, Event]] = []
        self._history: list[Event] = []
        self._next_sequence = 0
        self._handlers: dict[str, EventHandler] = {}
        self._clock = LogicalClock()
        self._current_event: Event | None = None

    @property
    def history(self) -> tuple[Event, ...]:
        return tuple(self._history)

    @property
    def pending_events(self) -> tuple[Event, ...]:
        return tuple(item[2] for item in sorted(self._queue))

    def register(self, event_type: str, handler: EventHandler) -> None:
        if not event_type or event_type in self._handlers:
            raise ValueError('event type must be non-empty and registered only once')
        self._handlers[event_type] = handler

    def schedule(
        self,
        time: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        parent_event_id: str | None = None,
    ) -> Event:
        if time < self.current_time:
            raise ValueError('cannot schedule an event in the past')
        if event_type not in self._handlers:
            raise ValueError(f'no handler registered for {event_type!r}')
        parent = parent_event_id or (
            self._current_event.event_id if self._current_event else None
        )
        known = {event.event_id for event in self._history} | {
            item[2].event_id for item in self._queue
        }
        if (
            parent is not None
            and parent not in known
            and (self._current_event is None or parent != self._current_event.event_id)
        ):
            raise ValueError(f'unknown causal parent event: {parent}')
        sequence = self._next_sequence
        self._next_sequence += 1
        event = Event(
            f'{self.timeline_id}:{sequence}',
            time,
            sequence,
            event_type,
            copy.deepcopy(payload or {}),
            parent,
        )
        heapq.heappush(self._queue, (time, sequence, event))
        self._clock.tick()
        return event

    def step(self) -> Event | None:
        if not self._queue:
            return None
        _, _, event = heapq.heappop(self._queue)
        self.current_time = event.time
        self._current_event = event
        try:
            self._handlers[event.event_type](event, self)
        except Exception:
            heapq.heappush(self._queue, (event.time, event.sequence, event))
            raise
        finally:
            self._current_event = None
        self._history.append(event)
        self._clock.tick()
        return event

    def run(
        self,
        *,
        until: int | None = None,
        max_events: int | None = None,
    ) -> tuple[Event, ...]:
        if until is not None and until < self.current_time:
            raise ValueError('until cannot precede current time')
        if max_events is not None and max_events < 0:
            raise ValueError('max_events must be non-negative')
        result: list[Event] = []
        while self._queue:
            if until is not None and self._queue[0][0] > until:
                break
            if max_events is not None and len(result) >= max_events:
                break
            event = self.step()
            if event is not None:
                result.append(event)
        if until is not None and self.current_time < until and not self._queue:
            self.current_time = until
        return tuple(result)

    def snapshot(self) -> EngineSnapshot:
        return EngineSnapshot(
            self.timeline_id,
            self.current_time,
            self._next_sequence,
            copy.deepcopy(self.pending_events),
            tuple(copy.deepcopy(self._history)),
            copy.deepcopy(self.state),
            self._clock.value,
        )

    @classmethod
    def from_snapshot(
        cls,
        snapshot: EngineSnapshot,
        handlers: dict[str, EventHandler] | None = None,
    ) -> SimulationEngine:
        engine = cls(snapshot.timeline_id)
        engine.current_time = snapshot.current_time
        engine._next_sequence = snapshot.next_sequence
        engine._history = list(copy.deepcopy(snapshot.history))
        engine.state = copy.deepcopy(snapshot.state)
        engine._clock.value = snapshot.logical_clock_value
        engine._handlers = dict(handlers or {})
        for event in copy.deepcopy(snapshot.queue):
            heapq.heappush(engine._queue, (event.time, event.sequence, event))
        return engine
