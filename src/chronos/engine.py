# ruff: noqa: E501, E701, E702
from __future__ import annotations

import copy
import heapq
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from chronos.clock import LogicalClock
from chronos.events import Event
from chronos.hybrid import Derivative, HybridIntegrationResult, RootFunction, integrate_to_root
from chronos.uncertainty import TimeInterval

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
    """Single-process deterministic scheduler with explicit hybrid integration boundaries."""

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
        self._initial_state: dict[str, Any] | None = None

    @property
    def initial_state(self) -> dict[str, Any]:
        """Return the state immediately before the first dispatched event."""
        return copy.deepcopy(self.state if self._initial_state is None else self._initial_state)

    @property
    def history(self) -> tuple[Event, ...]:
        """Return detached event copies so callers cannot rewrite recorded history."""
        return copy.deepcopy(tuple(self._history))

    @property
    def pending_events(self) -> tuple[Event, ...]:
        """Return detached queue entries so callers cannot mutate scheduled work."""
        return copy.deepcopy(tuple(item[2] for item in sorted(self._queue)))

    def register(self, event_type: str, handler: EventHandler) -> None:
        if not event_type or event_type in self._handlers:
            raise ValueError('event type must be non-empty and registered only once')
        self._handlers[event_type] = handler

    def schedule(self, time: int, event_type: str, payload: dict[str, Any] | None = None, *,
        parent_event_id: str | None = None) -> Event:
        if isinstance(time,bool) or not isinstance(time,int):
            raise ValueError('discrete event time must be an integer tick')
        if time < self.current_time:
            raise ValueError('cannot schedule an event in the past')
        if event_type not in self._handlers:
            raise ValueError(f'no handler registered for {event_type!r}')
        parent = parent_event_id or (self._current_event.event_id if self._current_event else None)
        known = {event.event_id for event in self._history} | {item[2].event_id for item in self._queue}
        if parent is not None and parent not in known and (self._current_event is None or parent != self._current_event.event_id):
            raise ValueError(f'unknown causal parent event: {parent}')
        sequence = self._next_sequence; self._next_sequence += 1
        event = Event(f'{self.timeline_id}:{sequence}',time,sequence,event_type,copy.deepcopy(payload or {}),parent)
        heapq.heappush(self._queue,(time,sequence,event)); self._clock.tick()
        # The queue owns its event. The returned value is a detached caller-owned copy.
        return copy.deepcopy(event)

    def integrate_continuous(self, rhs: Derivative, initial: tuple[float,...], *,
        start: float, stop: float, step: float,
        root_events: Mapping[str, tuple[str, RootFunction, dict[str, Any]]] | None = None,
        root_tolerance: float=1e-9) -> HybridIntegrationResult:
        """Integrate only to the next queued discrete boundary and schedule a root event.

        Continuous coordinates are real-valued. A detected root is represented on
        the integer event axis by ceil(root_time); the exact root time/state are
        retained in the event payload. The caller runs the event engine at that
        boundary and resumes integration from the returned root state/time.
        """
        if start < self.current_time or stop < start or not all(map(math.isfinite,(start,stop))):
            raise ValueError('continuous start/stop must be finite and not precede engine time')
        boundary=float(self._queue[0][0]) if self._queue else stop
        boundary=min(stop,boundary)
        roots={name:spec[1] for name,spec in (root_events or {}).items()}
        result=integrate_to_root(rhs,initial,start,boundary,step=step,roots=roots,tolerance=root_tolerance)
        if result.root_event is not None:
            spec=(root_events or {})[result.root_event.name]
            event_tick=max(self.current_time,math.ceil(result.root_event.time))
            payload={**spec[2],"root_name":result.root_event.name,
                "root_time":result.root_event.time,"root_state":list(result.root_event.state)}
            self.current_time=max(self.current_time,event_tick)
            self.schedule(event_tick,spec[0],payload)
        else:
            self.current_time=max(self.current_time,math.ceil(result.reached_boundary))
        return result

    def schedule_uncertain(self, interval: TimeInterval, event_type: str,
        payload: dict[str, Any] | None = None, *, policy: str = 'upper_bound') -> Event:
        """Schedule at ceil(interval.upper); preserves interval metadata for audit.

        This is a conservative latest-bound policy, not a claim that overlapping
        intervals have a physically known order.
        """
        if policy != 'upper_bound':
            raise ValueError("only the explicit upper_bound uncertainty policy is supported")
        event_payload = dict(payload or {})
        if "uncertain_time" in event_payload:
            raise ValueError("uncertain_time is reserved for scheduler metadata")
        event_payload["uncertain_time"] = {
            "lower": interval.lower, "upper": interval.upper, "policy": policy
        }
        tick = math.ceil(interval.upper)
        if tick < self.current_time:
            raise ValueError("uncertain interval ends before current engine time")
        return self.schedule(tick, event_type, event_payload)

    def step(self) -> Event | None:
        if not self._queue: return None
        if self._initial_state is None:
            self._initial_state = copy.deepcopy(self.state)
        state_before=copy.deepcopy(self.state); queue_before=copy.deepcopy(self._queue)
        next_sequence_before=self._next_sequence; clock_before=self._clock.value; time_before=self.current_time
        _,_,event=heapq.heappop(self._queue); self.current_time=event.time; self._current_event=event
        # Preserve the scheduled input separately from any handler-local mutation.
        recorded_event = copy.deepcopy(event)
        try:
            self._handlers[event.event_type](event,self)
        except Exception:
            self.state=state_before; self._queue=queue_before; self._next_sequence=next_sequence_before
            self._clock.value=clock_before; self.current_time=time_before
            raise
        finally:
            self._current_event=None
        self._history.append(recorded_event); self._clock.tick()
        return copy.deepcopy(recorded_event)

    def run(self, *, until: int | None=None, max_events: int | None=None) -> tuple[Event,...]:
        if until is not None and until<self.current_time: raise ValueError('until cannot precede current time')
        if max_events is not None and max_events<0: raise ValueError('max_events must be non-negative')
        result: list[Event] = []
        while self._queue:
            if until is not None and self._queue[0][0]>until: break
            if max_events is not None and len(result)>=max_events: break
            event=self.step()
            if event is not None: result.append(event)
        if until is not None and self.current_time<until and not self._queue: self.current_time=until
        return tuple(result)

    def snapshot(self) -> EngineSnapshot:
        return EngineSnapshot(self.timeline_id,self.current_time,self._next_sequence,
            copy.deepcopy(self.pending_events),tuple(copy.deepcopy(self._history)),
            copy.deepcopy(self.state),self._clock.value)

    @classmethod
    def from_snapshot(cls,snapshot: EngineSnapshot,handlers: dict[str,EventHandler] | None=None) -> SimulationEngine:
        engine=cls(snapshot.timeline_id); engine.current_time=snapshot.current_time
        engine._next_sequence=snapshot.next_sequence; engine._history=list(copy.deepcopy(snapshot.history))
        engine.state=copy.deepcopy(snapshot.state); engine._clock.value=snapshot.logical_clock_value
        engine._handlers=dict(handlers or {})
        for event in copy.deepcopy(snapshot.queue): heapq.heappush(engine._queue,(event.time,event.sequence,event))
        return engine
