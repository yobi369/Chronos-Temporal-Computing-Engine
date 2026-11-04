# Hybrid discrete/continuous simulation

Chronos supplies explicit RK4 primitives for smooth, non-stiff ODEs. Fixed-step RK4 is fourth order under its assumptions. The adaptive variant uses step doubling and estimates local error as (two half steps - one full step)/15; this is an estimator, not a rigorous global error bound. Stiff systems require a suitable implicit solver and are not supported here.

Continuous state is currently integrated as a pure numerical subsystem. Applications couple it to discrete events at explicit boundaries: integrate to the next event time, apply the discrete transition, then continue. There is no hidden scheduler coupling or event-root localization. Users must choose units, tolerances, discontinuity policy and state scaling.

Tests compare exponential decay with its analytic solution and check step refinement. These are numerical regression tests, not independent solver certification.
