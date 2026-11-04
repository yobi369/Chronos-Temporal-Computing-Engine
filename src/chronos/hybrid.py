# ruff: noqa: E701, E702, E501
"""Deterministic fixed-step and step-doubling RK4 integration primitives."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
import math

Vector = tuple[float, ...]
Derivative = Callable[[float, Vector], Vector]

@dataclass(frozen=True, slots=True)
class IntegrationResult:
    times: tuple[float, ...]
    states: tuple[Vector, ...]
    accepted_steps: int
    rejected_steps: int
    max_error_estimate: float

def _checked(value: Vector, dimension: int) -> Vector:
    if len(value) != dimension or any(not math.isfinite(x) for x in value):
        raise ValueError("derivative must return a finite vector of the state dimension")
    return value

def _add(a: Vector, b: Vector, scale: float) -> Vector:
    return tuple(x + scale*y for x, y in zip(a, b, strict=True))

def rk4_step(rhs: Derivative, t: float, y: Vector, h: float) -> Vector:
    """One classical explicit RK4 step; suitable only for non-stiff systems."""
    if not math.isfinite(t) or not math.isfinite(h) or h <= 0 or not y:
        raise ValueError("t must be finite, h positive and state non-empty")
    n=len(y)
    k1=_checked(rhs(t,y),n)
    k2=_checked(rhs(t+h/2,_add(y,k1,h/2)),n)
    k3=_checked(rhs(t+h/2,_add(y,k2,h/2)),n)
    k4=_checked(rhs(t+h,_add(y,k3,h)),n)
    result=tuple(v+h*(a+2*b+2*c+d)/6 for v,a,b,c,d in zip(y,k1,k2,k3,k4,strict=True))
    if any(not math.isfinite(x) for x in result):
        raise ArithmeticError("RK4 produced a non-finite state")
    return result

def integrate_rk4(rhs: Derivative, initial: Vector, start: float, stop: float, step: float) -> IntegrationResult:
    if not initial or any(not math.isfinite(x) for x in initial) or not (math.isfinite(start) and math.isfinite(stop) and stop >= start and math.isfinite(step) and step > 0):
        raise ValueError("invalid integration interval, step or initial state")
    times=[start]; states=[tuple(initial)]; t=start; y=tuple(initial)
    while t < stop:
        h=min(step,stop-t)
        y=rk4_step(rhs,t,y,h); t=min(stop,t+h)
        times.append(t); states.append(y)
    return IntegrationResult(tuple(times),tuple(states),len(times)-1,0,0.0)

def integrate_adaptive_rk4(rhs: Derivative, initial: Vector, start: float, stop: float, *,
    initial_step: float, atol: float=1e-9, rtol: float=1e-7, min_step: float=1e-12,
    max_step: float|None=None, max_steps: int=100000) -> IntegrationResult:
    """Step-doubling RK4 controller; error estimate is |two half steps - full step|/15."""
    if initial_step<=0 or atol<=0 or rtol<0 or min_step<=0 or max_steps<1 or stop<start:
        raise ValueError("invalid adaptive integration controls")
    cap=max_step if max_step is not None else max(initial_step,stop-start)
    if cap<=0: raise ValueError("max_step must be positive")
    t=start; y=tuple(initial); h=min(initial_step,cap); times=[t]; states=[y]
    accepted=rejected=0; max_error=0.0; attempts=0
    while t < stop:
        attempts+=1
        if attempts>max_steps: raise RuntimeError("adaptive RK4 exceeded max_steps")
        h=min(h,cap,stop-t)
        full=rk4_step(rhs,t,y,h)
        half=rk4_step(rhs,t,y,h/2)
        fine=rk4_step(rhs,t+h/2,half,h/2)
        errors=[abs(a-b)/15 for a,b in zip(fine,full,strict=True)]
        norm=max(e/(atol+rtol*max(abs(a),abs(b))) for e,a,b in zip(errors,y,fine,strict=True))
        max_error=max(max_error,max(errors,default=0.0))
        if norm<=1:
            y=tuple(v+(v-w)/15 for v,w in zip(fine,full,strict=True))
            t=min(stop,t+h); times.append(t); states.append(y); accepted+=1
        else: rejected+=1
        factor=2.0 if norm==0 else max(0.2,min(2.0,0.9*norm**(-0.2)))
        h*=factor
        if h<min_step and t<stop: raise RuntimeError("adaptive RK4 reached min_step")
    return IntegrationResult(tuple(times),tuple(states),accepted,rejected,max_error)
