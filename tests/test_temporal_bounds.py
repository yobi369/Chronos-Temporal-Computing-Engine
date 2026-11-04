import pytest
from chronos.temporal import (AlwaysWithin, Atom, EventuallyWithin, ModelCheckingLimitError,
    Release, bounded_model_check, evaluate)

def test_bounded_temporal_operators_and_release():
    yes=Atom(lambda state: state["ok"])
    no=Atom(lambda state: state["stop"])
    trace=({"ok":True,"stop":False},{"ok":True,"stop":True},{"ok":False,"stop":True})
    assert evaluate(EventuallyWithin(no,1),trace)
    assert evaluate(AlwaysWithin(yes,1),trace)
    assert not evaluate(AlwaysWithin(yes,2),trace)
    assert evaluate(Release(no,yes),trace)

def test_model_checker_enforces_path_budget_even_when_states_repeat():
    def branching(state):
        return [{"n":0},{"n":0}]
    with pytest.raises(ModelCheckingLimitError,match="max_traces"):
        bounded_model_check({"n":0},branching,Atom(lambda state: True),
            max_depth=4,max_states=2,max_traces=3)
