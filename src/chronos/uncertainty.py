# ruff: noqa: E501, E701, E702
"""Interval-valued time and probabilistic order propagation."""
from __future__ import annotations
from dataclasses import dataclass
import math
import random

@dataclass(frozen=True, order=True, slots=True)
class TimeInterval:
    lower: float
    upper: float
    def __post_init__(self) -> None:
        if not (math.isfinite(self.lower) and math.isfinite(self.upper)) or self.lower > self.upper:
            raise ValueError("time interval must be finite and lower <= upper")
    def definitely_before(self, other: TimeInterval) -> bool:
        return self.upper < other.lower
    def possibly_before(self, other: TimeInterval) -> bool:
        return self.lower < other.upper
    def overlaps(self, other: TimeInterval) -> bool:
        return not (self.definitely_before(other) or other.definitely_before(self))
    def intersection(self, other: TimeInterval) -> TimeInterval | None:
        lo=max(self.lower,other.lower); hi=min(self.upper,other.upper)
        return TimeInterval(lo,hi) if lo<=hi else None
    def hull(self, other: TimeInterval) -> TimeInterval:
        return TimeInterval(min(self.lower,other.lower),max(self.upper,other.upper))

def must_precede(a: TimeInterval,b: TimeInterval) -> bool:
    return a.upper < b.lower

def possible_orders(intervals: tuple[TimeInterval,...]) -> tuple[tuple[int,...],...]:
    if len(intervals)>8: raise ValueError("possible_orders is limited to 8 intervals")
    predecessors={i:{j for j in range(len(intervals)) if j!=i and must_precede(intervals[j],intervals[i])} for i in range(len(intervals))}
    results=[]
    def visit(prefix: tuple[int,...],remaining: frozenset[int]) -> None:
        if not remaining: results.append(prefix); return
        for item in sorted(i for i in remaining if not (predecessors[i]&remaining)):
            visit((*prefix,item),remaining-{item})
    visit((),frozenset(range(len(intervals))))
    return tuple(results)

@dataclass(frozen=True,slots=True)
class OrderProbability:
    order: tuple[int,...]
    count: int
    probability: float

@dataclass(frozen=True,slots=True)
class ProbabilityEstimate:
    samples: int
    seed: int
    outcomes: tuple[OrderProbability,...]

def propagate_order_probabilities(intervals: tuple[TimeInterval,...],*,samples: int=20000,seed: int=0) -> ProbabilityEstimate:
    """Independent-uniform Monte Carlo; output probabilities depend on this assumption."""
    if not intervals or len(intervals)>32 or samples<1: raise ValueError("invalid interval count or sample count")
    rng=random.Random(seed); counts: dict[tuple[int,...],int]={}
    for _ in range(samples):
        values=[rng.uniform(x.lower,x.upper) for x in intervals]
        order=tuple(sorted(range(len(values)),key=lambda i:(values[i],i)))
        counts[order]=counts.get(order,0)+1
    outcomes=tuple(OrderProbability(k,v,v/samples) for k,v in sorted(counts.items()))
    return ProbabilityEstimate(samples,seed,outcomes)
