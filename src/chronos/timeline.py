from dataclasses import dataclass
from chronos.engine import EngineSnapshot, EventHandler, SimulationEngine

@dataclass(frozen=True, slots=True)
class Timeline:
    """Named checkpoint; forks are isolated counterfactual continuations."""
    name: str
    snapshot: EngineSnapshot

    @classmethod
    def capture(cls, name: str, engine: SimulationEngine) -> 'Timeline':
        if not name:
            raise ValueError('timeline name must not be empty')
        return cls(name, engine.snapshot())

    def fork(self, name: str, *, handlers: dict[str, EventHandler] | None = None) -> SimulationEngine:
        if not name:
            raise ValueError('fork name must not be empty')
        s = self.snapshot
        branch = EngineSnapshot(name, s.current_time, s.next_sequence, s.queue, s.history, s.state, s.logical_clock_value)
        return SimulationEngine.from_snapshot(branch, handlers)
