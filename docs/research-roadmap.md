# Research and engineering roadmap

This roadmap separates implementable software capabilities from speculative physical interpretations. A completed software milestone is not evidence for a physical theory.

## Milestone 1 — deterministic temporal core

- [x] Discrete-event scheduler with stable ordering.
- [x] Declared event-parent provenance.
- [x] Lamport logical clock.
- [x] In-process snapshots and isolated timeline forks.
- [x] Vector clocks and happens-before comparison.
- [x] Causal provenance graph with ancestor and descendant queries.
- [x] Initial unit tests and CI workflow.

## Milestone 2 — reproducibility and formal semantics

- [x] Canonical, versioned event-log serialization with strict structural validation.
- [x] Local atomic event-log persistence with a bounded reader.
- [x] Deterministic replay from explicit initial inputs and recorded handler-generated events.
- [x] Final-state SHA-256 digest comparison during replay.
- [ ] Snapshot compatibility and migration policy.
- [ ] Property-based testing and differential testing against an independent scheduler.
- [ ] Temporal logic operators and bounded model-checking examples.

## Milestone 3 — research-grade simulation

- [ ] Hybrid discrete/continuous simulation with documented numerical solvers.
- [ ] Interval and uncertain-time semantics.
- [ ] Branch comparison reports and sensitivity analysis.
- [ ] Reproducible experiment manifests, seeds, and provenance.
- [ ] Performance benchmarks with fixed workloads and published methodology.

## Milestone 4 — distributed and collaborative execution

- [ ] Distributed event ingestion and causality reconciliation.
- [ ] Durable event store and checkpoint recovery.
- [ ] Deterministic partitioning and explicit concurrency semantics.
- [ ] Security model for untrusted simulation handlers and imported experiment files.

## Scientific boundary

Relativistic time dilation, quantum temporal models, closed timelike curves, and other speculative physical ideas are not implemented by the current engine. Any future module making physical predictions must define equations, assumptions, units, parameter provenance, and comparison against established reference results. A visual analogy or internally consistent simulation is not experimental confirmation.
