# ruff: noqa: E501, E701, E702
import pytest
from chronos.symbolic import Boolean,Compare,Field,Literal,SymbolicLimitError,canonical_independent_trace,symbolic_bounded_check

def test_symbolic_invariant_returns_counterexample():
    invariant=Boolean("and",(Compare("ge",Field("balance"),Literal(0)),Compare("le",Field("balance"),Literal(3))))
    result=symbolic_bounded_check({"balance":1},lambda s:[{"balance":s["balance"]+2}],
        invariant,max_depth=3)
    assert not result.holds
    assert result.counterexample[-1]["balance"]==5

def test_symbolic_state_limit_and_partial_order_canonicalization():
    with pytest.raises(SymbolicLimitError):
        symbolic_bounded_check({"n":0},lambda s:[{"n":s["n"]+1}],Compare("ge",Field("n"),Literal(0)),
            max_depth=5,max_states=2)
    def independent(a, b):
        return {a,b}=={"read-a","read-b"}
    assert canonical_independent_trace(("read-b","read-a","write"),independent)==("read-a","read-b","write")


def test_symbolic_checker_enforces_generated_path_budget():
    with pytest.raises(SymbolicLimitError,match="path"):
        symbolic_bounded_check({"n":0},lambda s:[{"n":1},{"n":1}],
            Compare("ge",Field("n"),Literal(0)),max_depth=3,max_states=2,max_paths=2)
