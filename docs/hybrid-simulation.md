# Hybrid discrete/continuous simulation

Chronos retains integer discrete logical ticks and adds an explicitly coupled real-valued ODE integration API.

## Engine integration

`SimulationEngine.integrate_continuous(rhs, initial, start, stop, step, root_events=...)` advances classical RK4 only as far as the earlier of:
- the caller's requested stop coordinate; or
- the next queued discrete event tick.

A root event is a named scalar function of `(time, state)`. Sign-changing crossings are localized by bisection. The engine schedules the associated discrete handler at `ceil(root_time)` and includes the unrounded root time and root state in the payload. The engine advances its integer logical clock to the ceiling of the reached continuous boundary. The caller should consume the root event, apply its discrete state transition, then resume integration from that integer boundary using the root state as the initial continuous state. Events already queued at the same rounded tick retain their earlier insertion sequence. This is an explicit quantization boundary, not exact real-time interleaving.

## Numerical assumptions and limitations

- Explicit classical RK4 is for non-stiff initial-value problems.
- Adaptive step-doubling compares one full step with two half steps; the estimate is local and is not a rigorous global error bound.
- Root localization requires a sign change. Tangential roots, multiple crossings inside one integration step, and discontinuous root functions can be missed.
- The first root is selected by localized time, then name for deterministic ties.
- The implementation does not yet provide dense output, automatic Jacobians, stiff solvers, event direction filters, or certified interval arithmetic.

Validate each model against analytic solutions, step refinement, conservation laws and an independent numerical solver before interpreting scientific results.
