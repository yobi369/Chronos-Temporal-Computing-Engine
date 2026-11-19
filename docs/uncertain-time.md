# Uncertain-time scheduling and probability propagation

`TimeInterval(lower, upper)` represents a closed finite interval. Strict definite precedence is `a.upper < b.lower`; overlap means the ordering is unresolved, not simultaneous.

## Execution policy

`SimulationEngine.schedule_uncertain(interval, ...)` currently supports only the explicit `upper_bound` policy. It schedules at `ceil(interval.upper)` and stores the original interval and policy in event payload metadata. This provides reproducible conservative dispatch at the latest bound. It does not preserve all possible orders as separate executions.

## Probabilistic propagation

`propagate_order_probabilities` draws one independent uniform sample from each interval per trial and records the resulting total order. The result includes sample count, seed, counts and estimated frequencies. These probabilities are conditional on the independent-uniform assumption; they are not objective probabilities inherent in the intervals.

For correlated clocks, non-uniform distributions, common-mode timing errors or empirical calibration, supply an appropriate future distribution model rather than interpreting the current Monte Carlo estimates as universal.
