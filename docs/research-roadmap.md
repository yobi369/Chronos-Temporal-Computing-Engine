# Research and engineering roadmap

A completed software milestone is not evidence for a physical theory.

## Milestone 1 — deterministic temporal core

- [x] Deterministic discrete-event scheduler.
- [x] Event-parent provenance, Lamport and vector clocks.
- [x] In-process snapshots, timeline forks, causal graph, initial tests and CI.

## Milestone 2 — reproducibility and formal semantics

- [x] Canonical versioned event logs, bounded local persistence, deterministic replay and final-state digest.
- [x] Versioned v2 snapshot format and v1-to-v2 in-memory migration.
- [x] Hypothesis scheduler property tests.
- [x] Differential tests against an independent sorted-list scheduler.
- [x] Finite-trace temporal operators and bounded explicit-state model checking.
- [x] Reproducible experiment manifests and paired scheduler microbenchmark harness.

## Research caveats

The reference scheduler is a separate small implementation of the same time/insertion-order contract, not a third-party simulator. Property tests explore generated bounded inputs, not all possible executions. Temporal logic uses finite traces, strong-next and finite-trace until semantics. Model checking is exhaustive only within the supplied transition relation, depth, and state limit. Benchmarks are environment-sensitive microbenchmarks requiring independent reproduction.

## Milestone 3 — research-grade simulation

- [ ] Hybrid discrete/continuous simulation with documented numerical solvers.
- [ ] Interval and uncertain-time semantics.
- [ ] Branch comparison reports and sensitivity analysis.
- [ ] Independent benchmark reproduction and statistical analysis.

## Milestone 4 — distributed execution

- [ ] Distributed event ingestion and causality reconciliation.
- [ ] Durable event store and checkpoint recovery.
- [ ] Deterministic partitioning and concurrency semantics.
- [ ] Security model for untrusted handlers and imported experiment files.

## Scientific boundary

Relativistic time dilation, quantum temporal models, closed timelike curves, and other speculative physical ideas are not implemented. Any future physical predictions require equations, assumptions, units, parameter provenance, and comparison with established reference results. Internal simulation consistency is not experimental confirmation.
