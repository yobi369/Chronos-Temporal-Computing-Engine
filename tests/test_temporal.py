import pytest
from chronos.temporal import (Always, And, Atom, Eventually, ModelCheckingLimitError,
    Next, Not, Or, Until, bounded_model_check, evaluate)

def test_finite_trace_temporal_operators():
    positive = Atom(lambda state: state["x"] > 0, "positive")
    done = Atom(lambda state: state["done"], "done")
    trace = ({"x": 1, "done": False}, {"x": 2, "done": False}, {"x": 3, "done": True})
    assert evaluate(Always(positive), trace)
    assert evaluate(Eventually(done), trace)
    assert evaluate(Next(positive), trace)
    assert evaluate(Until(positive, done), trace)
    assert evaluate(And(positive, Not(done)), trace)
    assert evaluate(Or(done, positive), trace)
    assert not evaluate(Next(done), trace, 2)

def test_bounded_model_check_finds_counterexample():
    def transitions(state):
        if state["n"] >= 2:
            return []
        return [{"n": state["n"] + 1}]
    invariant = Always(Atom(lambda state: state["n"] < 2, "n below two"))
    result = bounded_model_check({"n": 0}, transitions, invariant, max_depth=2)
    assert not result.holds
    assert result.counterexample is not None
    assert result.counterexample[-1]["n"] == 2

def test_bounded_model_check_accepts_safe_graph_and_enforces_state_limit():
    transitions = lambda state: [{"n": 0}] if state["n"] == 0 else []
    result = bounded_model_check({"n": 0}, transitions,
        Always(Atom(lambda state: state["n"] == 0)), max_depth=3)
    assert result.holds
    with pytest.raises(ModelCheckingLimitError):
        bounded_model_check({"n": 0}, lambda state: [{"n": state["n"] + 1}],
            Always(Atom(lambda state: True)), max_depth=4, max_states=2)
