# ruff: noqa: E701, E702, E501
"""Interval-valued time and partial-order semantics for uncertain timestamps."""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True, order=True, slots=True)
class TimeInterval:
    lower: float
    upper: float
    def __post_init__(self) -> None:
        if not (math.isfinite(self.lower) and math.isfinite(self.upper)) or self.lower>self.upper:
            raise ValueError("time interval must be finite and lower <= upper")
    def definitely_before(self, other: TimeInterval) -> bool:
        return self.upper < other.lower
    def possibly_before(self, other: TimeInterval) -> bool:
        return self.lower < other.upper
    def overlaps(self, other: TimeInterval) -> bool:
        return not (self.definitely_before(other) or other.definitely_before(self))
    def intersection(self, other: TimeInterval) -> "TimeInterval|None":
        lo=max(self.lower,other.lower); hi=min(self.upper,other.upper)
        return TimeInterval(lo,hi) if lo<=hi else None
    def hull(self, other: TimeInterval) -> TimeInterval:
        return TimeInterval(min(self.lower,other.lower),max(self.upper,other.upper))

def must_precede(a: TimeInterval, b: TimeInterval) -> bool:
    """Strict precedence only when every time in a is earlier than every time in b."""
    return a.upper < b.lower

def possible_orders(intervals: tuple[TimeInterval,...]) -> tuple[tuple[int,...],...]:
    """Enumerate topological orders of the definite-before relation; bounded to 8 items."""
    n=len(intervals)
    if n>8: raise ValueError("possible_orders is limited to 8 intervals")
    edges={i:{j for j in range(n) if i!=j and must_precede(intervals[i],intervals[j])} for i in range(n)}
    results=[]
    def visit(prefix: tuple[int,...], remaining: frozenset[int]) -> None:
        if not remaining: results.append(prefix); return
        ready=sorted(i for i in remaining if not (edges[i] & remaining) and all(i not in edges[j] for j in remaining))
        # A node is ready when all its predecessors have already been emitted.
        ready=sorted(i for i in remaining if all(not must_precede(intervals[j],intervals[i]) or j not in remaining for j in remaining if j!=i))
        for i in ready: visit((*prefix,i),remaining-{i})
    visit((),frozenset(range(n)))
    return tuple(results)
