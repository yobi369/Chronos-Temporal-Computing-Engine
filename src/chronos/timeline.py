from dataclasses import dataclass

from chronos.engine import EngineSnapshot, EventHandler, SimulationEngine


@dataclass(frozen=True, slots=True)
class Timeline:
    """Named checkpoint; forks are isolated counterfactual continuations."""

    name: str
    snapshot: EngineSnapshot

    @classmethod
    def capture(cls, name: str, engine: SimulationEngine) -> Timeline:
        if not name:
            raise ValueError('timeline name must not be empty')
        return cls(name, engine.snapshot())

    def fork(
        self,
        name: str,
        *,
        handlers: dict[str, EventHandler] | None = None,
    ) -> SimulationEngine:
        if not name:
            raise ValueError('fork name must not be empty')
        snapshot = self.snapshot
        branch = EngineSnapshot(
            name,
            snapshot.current_time,
            snapshot.next_sequence,
            snapshot.queue,
            snapshot.history,
            snapshot.state,
            snapshot.logical_clock_value,
        )
        return SimulationEngine.from_snapshot(branch, handlers)
