from collections.abc import Iterable
from chronos.events import Event

def validate_event_log(events: Iterable[Event]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    sequences: set[int] = set()
    previous: tuple[int, int] | None = None
    for index, event in enumerate(events):
        if event.event_id in ids:
            errors.append(f'event[{index}]: duplicate id {event.event_id!r}')
        if event.sequence in sequences:
            errors.append(f'event[{index}]: duplicate sequence {event.sequence}')
        key = (event.time, event.sequence)
        if previous is not None and key < previous:
            errors.append(f'event[{index}]: execution order regressed')
        if event.parent_event_id is not None and event.parent_event_id not in ids:
            errors.append(f'event[{index}]: causal parent {event.parent_event_id!r} does not precede child')
        ids.add(event.event_id)
        sequences.add(event.sequence)
        previous = key
    return errors
