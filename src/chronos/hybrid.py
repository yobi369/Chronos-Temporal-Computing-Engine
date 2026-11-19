# ruff: noqa: E501, E701, E702
"""Classical RK4 solvers and event localization for hybrid simulations."""
from __future__ import annotations
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import math

Vector = tuple[float, ...]
Derivative = Callable[[float, Vector], Vector]
RootFunction = Callable[[float, Vector], float]

@dataclass(frozen=True, slots=True)
class IntegrationResult:
    times: tuple[float, ...]
    states: tuple[Vector, ...]
    accepted_steps: int
    rejected_steps: int
    max_error_estimate: float

@dataclass(frozen=True, slots=True)
class RootEvent:
    name: str
    time: float
    state: Vector
    value_before: float
    value_after: float

@dataclass(frozen=True, slots=True)
class HybridIntegrationResult:
    integration: IntegrationResult
    root_event: RootEvent | None
    reached_boundary: float

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
    """Step-doubling RK4 controller; estimate is |two half steps - full step|/15."""
    controls=(start,stop,initial_step,atol,rtol,min_step)
    if (not initial or not all(math.isfinite(x) for x in initial)
        or not all(math.isfinite(x) for x in controls)
        or initial_step<=0 or atol<=0 or rtol<0 or min_step<=0
        or max_steps<1 or stop<start):
        raise ValueError("invalid adaptive integration controls or initial state")
    cap=max_step if max_step is not None else max(initial_step,stop-start)
    if not math.isfinite(cap) or cap<=0: raise ValueError("max_step must be finite and positive")
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

def _crosses(a: float, b: float) -> bool:
    return (a < 0 < b) or (b < 0 < a) or (b == 0.0 and a != 0.0)

def _locate_root(rhs: Derivative, root: RootFunction, t0: float, y0: Vector,
    t1: float, y1: Vector, *, tolerance: float, max_iterations: int) -> tuple[float,Vector,float,float]:
    lo=t0; hi=t1; vlo=root(lo,y0); vhi=root(hi,y1)
    if abs(vlo)<=tolerance: return lo,y0,vlo,vlo
    if abs(vhi)<=tolerance: return hi,y1,vlo,vhi
    for _ in range(max_iterations):
        mid=(lo+hi)/2
        ym=rk4_step(rhs,t0,y0,mid-t0)
        vm=root(mid,ym)
        if abs(vm)<=tolerance or hi-lo<=tolerance: return mid,ym,vlo,vhi
        if (vlo<0 and vm>0) or (vlo>0 and vm<0):
            hi=mid; vhi=vm
        else:
            lo=mid; vlo=vm
    mid=(lo+hi)/2
    return mid,rk4_step(rhs,t0,y0,mid-t0),vlo,vhi

def integrate_to_root(rhs: Derivative, initial: Vector, start: float, stop: float, *,
    step: float, roots: Mapping[str,RootFunction], tolerance: float=1e-9,
    max_root_iterations: int=80) -> HybridIntegrationResult:
    """Integrate to the first detected sign-changing root or the hard boundary.

    Roots are localized by bisection, reintegrating from the beginning of the
    enclosing RK4 step. Tangential roots without a sign change are not detected.
    """
    if not math.isfinite(tolerance) or tolerance<=0 or max_root_iterations<1:
        raise ValueError("root tolerance and iteration bound must be positive")
    if (not initial or not all(math.isfinite(x) for x in initial)
        or not all(math.isfinite(x) for x in (start,stop,step)) or step<=0 or stop<start):
        raise ValueError("invalid hybrid integration interval or step")
    for name,fn in roots.items():
        if not name or not math.isfinite(fn(start,tuple(initial))):
            raise ValueError("root functions need names and finite initial values")
    times=[start]; states=[tuple(initial)]; t=start; y=tuple(initial)
    while t<stop:
        h=min(step,stop-t); next_y=rk4_step(rhs,t,y,h); next_t=t+h
        candidates=[]
        for name,fn in roots.items():
            before=fn(t,y); after=fn(next_t,next_y)
            if not math.isfinite(before) or not math.isfinite(after):
                raise ValueError(f"root function {name!r} returned a non-finite value")
            if _crosses(before,after):
                rt,ry,v0,v1=_locate_root(rhs,fn,t,y,next_t,next_y,
                    tolerance=tolerance,max_iterations=max_root_iterations)
                if rt>start+tolerance:
                    candidates.append(RootEvent(name,rt,ry,v0,v1))
        if candidates:
            event=min(candidates,key=lambda item:(item.time,item.name))
            if event.time>times[-1]:
                times.append(event.time); states.append(event.state)
            result=IntegrationResult(tuple(times),tuple(states),len(times)-1,0,0.0)
            return HybridIntegrationResult(result,event,event.time)
        t=next_t; y=next_y; times.append(t); states.append(y)
    return HybridIntegrationResult(IntegrationResult(tuple(times),tuple(states),len(times)-1,0,0.0),None,stop)
