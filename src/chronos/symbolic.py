# ruff: noqa: E501, E701, E702
"""Symbolic predicates and bounded reachability over finite transition systems."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from collections.abc import Callable, Iterable, Mapping
from typing import Any
from chronos.event_log import state_digest

State = Mapping[str,Any]

class Expr:
    def evaluate(self,state: State) -> Any:
        raise NotImplementedError

@dataclass(frozen=True,slots=True)
class Field(Expr):
    name: str
    def evaluate(self,state: State) -> Any:
        if self.name not in state: raise KeyError(f"symbolic state has no field {self.name!r}")
        return state[self.name]

@dataclass(frozen=True,slots=True)
class Literal(Expr):
    value: Any
    def evaluate(self,state: State) -> Any:
        return self.value

@dataclass(frozen=True,slots=True)
class Compare(Expr):
    operator: str
    left: Expr
    right: Expr
    def evaluate(self,state: State) -> bool:
        a=self.left.evaluate(state); b=self.right.evaluate(state)
        operations={"eq":lambda:a==b,"ne":lambda:a!=b,"lt":lambda:a<b,
            "le":lambda:a<=b,"gt":lambda:a>b,"ge":lambda:a>=b}
        if self.operator not in operations: raise ValueError("unsupported symbolic comparison")
        return bool(operations[self.operator]())

@dataclass(frozen=True,slots=True)
class Boolean(Expr):
    operator: str
    operands: tuple[Expr,...]
    def evaluate(self,state: State) -> bool:
        if self.operator=="not":
            if len(self.operands)!=1: raise ValueError("not requires one operand")
            return not bool(self.operands[0].evaluate(state))
        if self.operator=="and": return all(bool(x.evaluate(state)) for x in self.operands)
        if self.operator=="or": return any(bool(x.evaluate(state)) for x in self.operands)
        raise ValueError("unsupported symbolic boolean operator")

@dataclass(frozen=True,slots=True)
class SymbolicCheckResult:
    holds: bool
    explored_states: int
    counterexample: tuple[dict[str,Any],...] | None
    depth_bound: int

class SymbolicLimitError(RuntimeError):
    pass

def symbolic_bounded_check(initial: dict[str,Any],
    transitions: Callable[[dict[str,Any]],Iterable[dict[str,Any]]],
    invariant: Expr, *, max_depth: int, max_states: int=10000, max_paths: int=100000) -> SymbolicCheckResult:
    """Check a symbolic state predicate over all reachable states up to max_depth."""
    if max_depth<0 or max_states<1 or max_paths<1: raise ValueError("invalid symbolic exploration bounds")
    state_digest(initial)
    queue=deque([(initial,(initial,),0)]); seen={state_digest(initial)}; generated=1
    while queue:
        state,trace,depth=queue.popleft()
        if not bool(invariant.evaluate(state)):
            return SymbolicCheckResult(False,len(seen),tuple(dict(x) for x in trace),max_depth)
        if depth>=max_depth: continue
        successors=list(transitions(dict(state)))
        if not successors: successors=[dict(state)]
        for nxt in successors:
            key=state_digest(nxt)
            if key not in seen:
                if len(seen)>=max_states: raise SymbolicLimitError("symbolic state limit exceeded")
                seen.add(key)
            generated+=1
            if generated>max_paths: raise SymbolicLimitError("symbolic path limit exceeded")
            queue.append((nxt,(*trace,nxt),depth+1))
    return SymbolicCheckResult(True,len(seen),None,max_depth)

def canonical_independent_trace(actions: tuple[str,...],
    independent: Callable[[str,str],bool]) -> tuple[str,...]:
    """Canonicalize labels under adjacent swaps; soundness of independence is caller-owned."""
    result=list(actions); changed=True
    while changed:
        changed=False
        for index in range(len(result)-1):
            left,right=result[index:index+2]
            if left>right and independent(left,right):
                result[index],result[index+1]=right,left; changed=True
    return tuple(result)
