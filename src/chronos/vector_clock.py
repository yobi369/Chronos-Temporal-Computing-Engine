from dataclasses import dataclass, field


@dataclass
class VectorClock:
    """Vector clock for reasoning about distributed happens-before order."""

    values: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if any(not process or value < 0 for process, value in self.values.items()):
            raise ValueError('process names must be non-empty and clock values non-negative')

    def tick(self, process: str) -> dict[str, int]:
        if not process:
            raise ValueError('process name must not be empty')
        self.values[process] = self.values.get(process, 0) + 1
        return dict(self.values)

    def merge(self, other: VectorClock, process: str) -> dict[str, int]:
        if not process:
            raise ValueError('process name must not be empty')
        keys = self.values.keys() | other.values.keys()
        self.values = {
            key: max(self.values.get(key, 0), other.values.get(key, 0))
            for key in keys
        }
        self.values[process] = self.values.get(process, 0) + 1
        return dict(self.values)

    def happens_before(self, other: VectorClock) -> bool:
        keys = self.values.keys() | other.values.keys()
        no_greater = all(
            self.values.get(key, 0) <= other.values.get(key, 0) for key in keys
        )
        strictly_less = any(
            self.values.get(key, 0) < other.values.get(key, 0) for key in keys
        )
        return no_greater and strictly_less

    def concurrent_with(self, other: VectorClock) -> bool:
        return not self.happens_before(other) and not other.happens_before(self)
