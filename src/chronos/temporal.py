"""Finite-trace temporal logic and bounded explicit-state model checking."""
from __future__ import annotations
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from chronos.event_log import state_digest

State = Mapping[str, Any]
class Formula:
    """Marker base class for temporal formulas."""
@dataclass(frozen=True)
class Atom(Formula):
    predicate: Callable[[State], bool]
    name: str = "atom"
@dataclass(frozen=True)
class Not(Formula):
    operand: Formula
@dataclass(frozen=True)
class And(Formula):
    left: Formula
    right: Formula
@dataclass(frozen=True)
class Or(Formula):
    left: Formula
    right: Formula
@dataclass(frozen=True)
class Next(Formula):
    operand: Formula
@dataclass(frozen=True)
class Always(Formula):
    operand: Formula
@dataclass(frozen=True)
class Eventually(Formula):
    operand: Formula
@dataclass(frozen=True)
class Until(Formula):
    left: Formula
    right: Formula
@dataclass(frozen=True)
class Release(Formula):
    left: Formula
    right: Formula
@dataclass(frozen=True)
class EventuallyWithin(Formula):
    operand: Formula
    steps: int
@dataclass(frozen=True)
class AlwaysWithin(Formula):
    operand: Formula
    steps: int

def evaluate(formula: Formula, trace: tuple[State, ...], index: int = 0) -> bool:
    """Evaluate finite-trace LTL; bounded operators count transitions, not seconds."""
    if not trace or index < 0 or index >= len(trace):
        return False
    if isinstance(formula, Atom): return bool(formula.predicate(trace[index]))
    if isinstance(formula, Not): return not evaluate(formula.operand, trace, index)
    if isinstance(formula, And): return evaluate(formula.left, trace, index) and evaluate(formula.right, trace, index)
    if isinstance(formula, Or): return evaluate(formula.left, trace, index) or evaluate(formula.right, trace, index)
    if isinstance(formula, Next): return evaluate(formula.operand, trace, index+1)
    if isinstance(formula, Always): return all(evaluate(formula.operand,trace,p) for p in range(index,len(trace)))
    if isinstance(formula, Eventually): return any(evaluate(formula.operand,trace,p) for p in range(index,len(trace)))
    if isinstance(formula, EventuallyWithin):
        if formula.steps<0: raise ValueError("steps must be non-negative")
        return any(evaluate(formula.operand,trace,p) for p in range(index,min(len(trace),index+formula.steps+1)))
    if isinstance(formula, AlwaysWithin):
        if formula.steps<0: raise ValueError("steps must be non-negative")
        return all(evaluate(formula.operand,trace,p) for p in range(index,min(len(trace),index+formula.steps+1)))
    if isinstance(formula, Until):
        for pos in range(index,len(trace)):
            if evaluate(formula.right,trace,pos):
                return all(evaluate(formula.left,trace,p) for p in range(index,pos))
            if not evaluate(formula.left,trace,pos): return False
        return False
    if isinstance(formula, Release):
        # R is the finite-trace dual of strong Until: not(not-left U not-right).
        return not evaluate(Until(Not(formula.left),Not(formula.right)),trace,index)
    raise TypeError(f"unsupported temporal formula: {type(formula).__name__}")

@dataclass(frozen=True)
class ModelCheckResult:
    holds: bool
    explored_states: int
    completed_traces: int
    counterexample: tuple[dict[str, Any], ...] | None
    depth_bound: int
    state_bound: int
    trace_bound: int

class ModelCheckingLimitError(RuntimeError):
    """Raised when an explicit exploration budget is exceeded."""

def bounded_model_check(initial: dict[str, Any],
    transitions: Callable[[dict[str, Any]], Iterable[dict[str, Any]]],
    formula: Formula, *, max_depth: int, max_states: int=10_000,
    max_traces: int=100_000) -> ModelCheckResult:
    """Check all paths to a finite depth; deadlocked states stutter.

    The state, depth and generated-path budgets are independent hard limits.
    This is exhaustive only for the supplied transition relation and bounds.
    """
    if max_depth<0 or max_states<1 or max_traces<1:
        raise ValueError("max_depth must be non-negative and state/trace limits positive")
    state_digest(initial)
    queue: deque[tuple[dict[str,Any],tuple[dict[str,Any],...]]]=deque([(initial,(initial,))])
    seen={state_digest(initial)}; completed=0; generated=1
    while queue:
        state,trace=queue.popleft()
        if len(trace)-1==max_depth:
            completed+=1
            if not evaluate(formula,trace):
                return ModelCheckResult(False,len(seen),completed,tuple(dict(x) for x in trace),max_depth,max_states,max_traces)
            continue
        successors=list(transitions(dict(state)))
        if not successors: successors=[dict(state)]
        for successor in successors:
            key=state_digest(successor)
            if key not in seen:
                if len(seen)>=max_states:
                    raise ModelCheckingLimitError(f"state exploration exceeded max_states={max_states}")
                seen.add(key)
            generated+=1
            if generated>max_traces:
                raise ModelCheckingLimitError(f"path exploration exceeded max_traces={max_traces}")
            queue.append((successor,(*trace,successor)))
    return ModelCheckResult(True,len(seen),completed,None,max_depth,max_states,max_traces)
