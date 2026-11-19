from hypothesis import given, settings, strategies as st

from chronos.engine import SimulationEngine
from chronos.event_log import (
    EventInput,
    EventLog,
    PayloadSchema,
    event_log_from_json,
    event_log_to_json,
    read_event_log,
    replay_event_log,
    state_digest,
    write_event_log,
)


def accumulate(event, simulation):
    simulation.state["total"] = simulation.state.get("total", 0) + event.payload["delta"]


def replay_handlers():
    return {"accumulate": accumulate}


@given(
    st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=100),
            st.integers(min_value=-1000, max_value=1000),
        ),
        min_size=0,
        max_size=30,
    )
)
@settings(max_examples=40, deadline=None)
def test_randomized_input_histories_replay_to_identical_state_and_history(samples):
    engine = SimulationEngine("randomized-replay")
    engine.register("accumulate", accumulate)
    inputs = tuple(
        EventInput(time, "accumulate", {"delta": delta})
        for time, delta in samples
    )
    for item in inputs:
        engine.schedule(item.time, item.event_type, item.payload)
    engine.run()

    log = EventLog.capture(
        engine,
        inputs,
        payload_schemas={
            "accumulate": PayloadSchema(required={"delta": "integer"})
        },
    )
    persisted = event_log_from_json(event_log_to_json(log))
    replayed = replay_event_log(persisted, replay_handlers())

    assert replayed.history == engine.history
    assert state_digest(replayed.state) == log.final_state_digest


def test_long_event_history_persists_and_replays_from_fresh_engine(tmp_path):
    engine = SimulationEngine("long-replay")
    engine.register("accumulate", accumulate)
    inputs = tuple(
        EventInput(index, "accumulate", {"delta": (index % 7) - 3})
        for index in range(4096)
    )
    for item in inputs:
        engine.schedule(item.time, item.event_type, item.payload)
    engine.run()

    log = EventLog.capture(
        engine,
        inputs,
        payload_schemas={
            "accumulate": PayloadSchema(required={"delta": "integer"})
        },
    )
    path = tmp_path / "long-history.chronos.json"
    write_event_log(path, log)
    restored = read_event_log(path)
    replayed = replay_event_log(restored, replay_handlers())

    assert len(replayed.history) == 4096
    assert replayed.history == engine.history
    assert state_digest(replayed.state) == log.final_state_digest
