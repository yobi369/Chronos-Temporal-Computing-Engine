from hypothesis import given, settings, strategies as st
from chronos.engine import SimulationEngine

def independent_reference_schedule(events):
    """Small sorted-list model that does not use Chronos scheduler internals."""
    pending = [(time, ordinal, payload) for ordinal, (time, payload) in enumerate(events)]
    output = []
    while pending:
        pending.sort(key=lambda item: (item[0], item[1]))
        output.append(pending.pop(0))
    return output

@given(st.lists(st.tuples(st.integers(min_value=0, max_value=30),
    st.integers(min_value=-1000, max_value=1000)), min_size=0, max_size=80))
@settings(max_examples=100, deadline=None)
def test_chronos_matches_independent_sorted_list_scheduler(generated):
    engine = SimulationEngine("differential")
    actual = []
    engine.register("record", lambda event, _: actual.append(
        (event.time, event.sequence, event.payload["value"])))
    for time, value in generated:
        engine.schedule(time, "record", {"value": value})
    engine.run()
    expected = independent_reference_schedule(generated)
    assert actual == expected
