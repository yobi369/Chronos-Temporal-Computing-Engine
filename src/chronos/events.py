from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    """Event on an experiment-defined discrete logical-time axis."""

    event_id: str
    time: int
    sequence: int
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    parent_event_id: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id or not self.event_type:
            raise ValueError('event_id and event_type must not be empty')
        if self.time < 0 or self.sequence < 0:
            raise ValueError('time and sequence must be non-negative')
