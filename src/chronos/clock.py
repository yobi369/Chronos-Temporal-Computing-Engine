from dataclasses import dataclass


@dataclass
class LogicalClock:
    """Lamport-style ordering counter, not a physical clock."""

    value: int = 0

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError('logical clock value must be non-negative')

    def tick(self) -> int:
        self.value += 1
        return self.value

    def observe(self, remote_value: int) -> int:
        if remote_value < 0:
            raise ValueError('remote logical clock value must be non-negative')
        self.value = max(self.value, remote_value) + 1
        return self.value
