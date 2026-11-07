import pytest

from chronos.engine import SimulationEngine
from chronos.validation import validate_event_log


def test_events_execute_in_stable_time_and_insertion_order():
    engine = SimulationEngine()
    seen = []
    engine.register('record', lambda event, _: seen.append(event.payload['value']))
    engine.schedule(4, 'record', {'value': 'late'})
    engine.schedule(2, 'record', {'value': 'first'})
    engine.schedule(2, 'record', {'value': 'second'})
    engine.run()
    assert seen == ['first', 'second', 'late']
    assert validate_event_log(engine.history) == []


def test_child_event_inherits_parent_provenance():
    engine = SimulationEngine()
    engine.register('child', lambda event, _: None)

    def parent(event, simulation):
        simulation.schedule(3, 'child')

    engine.register('parent', parent)
    root = engine.schedule(1, 'parent')
    engine.run()
    assert engine.history[1].parent_event_id == root.event_id
    assert validate_event_log(engine.history) == []


def test_past_schedule_and_unknown_parent_are_rejected():
    engine = SimulationEngine()
    engine.register('noop', lambda event, _: None)
    engine.schedule(1, 'noop')
    engine.run()
    with pytest.raises(ValueError, match='past'):
        engine.schedule(0, 'noop')
    with pytest.raises(ValueError, match='unknown causal parent'):
        engine.schedule(2, 'noop', parent_event_id='missing')


def test_run_respects_time_and_count_bounds():
    engine = SimulationEngine()
    engine.register('noop', lambda event, _: None)
    for time in (2, 5, 7):
        engine.schedule(time, 'noop')
    assert len(engine.run(until=5, max_events=1)) == 1
    assert engine.current_time == 2
    assert len(engine.run(until=5)) == 1
    assert engine.current_time == 5
    assert len(engine.pending_events) == 1


def test_handler_failure_rolls_back_engine_managed_mutations():
    engine = SimulationEngine()
    engine.state["stable"] = {"count": 1}

    def fail_after_mutating(event, simulation):
        simulation.state["stable"]["count"] = 99
        simulation.state["partial"] = True
        simulation.schedule(event.time + 1, "noop")
        raise RuntimeError("simulated handler failure")

    engine.register("fail", fail_after_mutating)
    engine.register("noop", lambda event, _: None)
    original = engine.schedule(5, "fail")

    with pytest.raises(RuntimeError, match="simulated handler failure"):
        engine.step()

    assert engine.state == {"stable": {"count": 1}}
    assert engine.pending_events == (original,)
    assert engine.current_time == 0
    assert engine.snapshot().next_sequence == 1
    assert engine.history == ()
