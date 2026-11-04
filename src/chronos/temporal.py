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

def evaluate(formula: Formula, trace: tuple[State, ...], index: int = 0) -> bool:
    """Evaluate finite-trace LTL with strong-next and finite-trace until semantics."""
    if not trace or index < 0 or index >= len(trace):
        return False
    if isinstance(formula, Atom):
        return bool(formula.predicate(trace[index]))
    if isinstance(formula, Not):
        return not evaluate(formula.operand, trace, index)
    if isinstance(formula, And):
        return evaluate(formula.left, trace, index) and evaluate(formula.right, trace, index)
    if isinstance(formula, Or):
        return evaluate(formula.left, trace, index) or evaluate(formula.right, trace, index)
    if isinstance(formula, Next):
        return evaluate(formula.operand, trace, index + 1)
    if isinstance(formula, Always):
        return all(evaluate(formula.operand, trace, pos) for pos in range(index, len(trace)))
    if isinstance(formula, Eventually):
        return any(evaluate(formula.operand, trace, pos) for pos in range(index, len(trace)))
    if isinstance(formula, Until):
        for pos in range(index, len(trace)):
            if evaluate(formula.right, trace, pos):
                return all(evaluate(formula.left, trace, prior) for prior in range(index, pos))
            if not evaluate(formula.left, trace, pos):
                return False
        return False
    raise TypeError(f"unsupported temporal formula: {type(formula).__name__}")

@dataclass(frozen=True)
class ModelCheckResult:
    holds: bool
    explored_states: int
    completed_traces: int
    counterexample: tuple[dict[str, Any], ...] | None
    depth_bound: int
    state_bound: int

class ModelCheckingLimitError(RuntimeError):
    """Raised when exhaustive exploration exceeds a caller-supplied bound."""

def bounded_model_check(initial: dict[str, Any],
    transitions: Callable[[dict[str, Any]], Iterable[dict[str, Any]]],
    formula: Formula, *, max_depth: int, max_states: int = 10_000) -> ModelCheckResult:
    """Check all paths to a finite depth; deadlocked states stutter.

    This is exhaustive only for the supplied transition graph and explicit bounds.
    """
    if max_depth < 0 or max_states < 1:
        raise ValueError("max_depth must be non-negative and max_states must be positive")
    state_digest(initial)
    queue: deque[tuple[dict[str, Any], tuple[dict[str, Any], ...]]] = deque(
        [(initial, (initial,))]
    )
    seen = {state_digest(initial)}
    completed = 0
    while queue:
        state, trace = queue.popleft()
        if len(trace) - 1 == max_depth:
            completed += 1
            if not evaluate(formula, trace):
                return ModelCheckResult(False, len(seen), completed,
                    tuple(dict(item) for item in trace), max_depth, max_states)
            continue
        successors = list(transitions(dict(state)))
        if not successors:
            successors = [dict(state)]
        for successor in successors:
            key = state_digest(successor)
            if key not in seen:
                if len(seen) >= max_states:
                    raise ModelCheckingLimitError(f"state exploration exceeded max_states={max_states}")
                seen.add(key)
            queue.append((successor, (*trace, successor)))
    return ModelCheckResult(True, len(seen), completed, None, max_depth, max_states)
