from __future__ import annotations

from dataclasses import dataclass

from chronos.engine import EngineSnapshot, EventHandler, SimulationEngine


def _fork_snapshot(snapshot: EngineSnapshot, name: str) -> EngineSnapshot:
    """Create the exact child checkpoint used by Timeline.fork and replay."""
    if not name:
        raise ValueError("fork name must not be empty")
    return EngineSnapshot(
        name,
        snapshot.current_time,
        snapshot.next_sequence,
        snapshot.queue,
        snapshot.history,
        snapshot.state,
        snapshot.logical_clock_value,
    )


@dataclass(frozen=True, slots=True)
class Timeline:
    """Named checkpoint; forks are isolated counterfactual continuations."""

    name: str
    snapshot: EngineSnapshot

    @classmethod
    def capture(cls, name: str, engine: SimulationEngine) -> Timeline:
        if not name:
            raise ValueError("timeline name must not be empty")
        return cls(name, engine.snapshot())

    def fork(
        self,
        name: str,
        *,
        handlers: dict[str, EventHandler] | None = None,
    ) -> SimulationEngine:
        branch = _fork_snapshot(self.snapshot, name)
        return SimulationEngine.from_snapshot(branch, handlers)
