from hypothesis import given, settings, strategies as st
from chronos.engine import SimulationEngine

@given(st.lists(st.integers(min_value=0, max_value=50), min_size=0, max_size=100))
@settings(max_examples=100, deadline=None)
def test_scheduler_orders_arbitrary_event_times_stably(times):
    engine = SimulationEngine()
    observed = []
    engine.register("record", lambda event, _: observed.append((event.time, event.sequence)))
    for time in times:
        engine.schedule(time, "record")
    engine.run()
    assert observed == sorted((time, sequence) for sequence, time in enumerate(times))

@given(st.lists(st.dictionaries(keys=st.text(min_size=1, max_size=8),
    values=st.integers(min_value=-100, max_value=100), max_size=5),
    min_size=0, max_size=20))
@settings(max_examples=60, deadline=None)
def test_scheduled_payloads_are_copied_at_submission(payloads):
    engine = SimulationEngine()
    observed = []
    engine.register("record", lambda event, _: observed.append(event.payload))
    for payload in payloads:
        engine.schedule(1, "record", payload)
        payload["mutated_after_schedule"] = True
    engine.run()
    assert all("mutated_after_schedule" not in payload for payload in observed)
