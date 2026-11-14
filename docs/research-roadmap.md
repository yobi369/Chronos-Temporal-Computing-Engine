# Research and engineering roadmap

A completed software milestone is not evidence for a physical theory.

## Milestone 1 — deterministic temporal core
- [x] Deterministic discrete-event scheduler.
- [x] Event-parent provenance, Lamport and vector clocks.
- [x] In-process snapshots, isolated timeline forks, causal graph, initial tests and CI.

## Milestone 2 — reproducibility and formal semantics
- [x] Canonical versioned event logs, bounded local persistence, deterministic replay and final-state digest.
- [x] Versioned v2 snapshot format and v1-to-v2 in-memory migration.
- [x] Hypothesis scheduler properties and differential reference checks.
- [x] Finite-trace temporal operators and bounded explicit-state model checking.
- [x] Reproducible manifests and scheduler microbenchmark harness.

## Milestone 3 — hybrid and uncertain-time research
- [x] Fixed-step classical RK4 and adaptive step-doubling RK4 for non-stiff ODEs.
- [x] Interval-valued timestamps, definite precedence and bounded linear-extension enumeration.
- [x] Bounded temporal operators and Release semantics.
- [x] Independent paired-run statistical analysis protocol and raw sample capture.
- [x] Durable single-writer checkpoint generations with integrity verification and recovery tests.

## Milestone 4 — distributed event semantics
- [x] Distributed event envelopes, duplicate/conflict detection and deterministic causal topological reconciliation.
- [x] HMAC-authenticated messages and acknowledgements, durable SQLite WAL inbox/outbox, retry backoff, deduplication, and at-least-once handler processing.
- [ ] Partition ownership, membership epochs, concurrent state conflict policy and distributed fault injection.
- [ ] Multi-node independent implementation and network-partition testing.

## Milestone 5 — integrated hybrid, uncertainty and worker execution
- [x] Couple RK4 integration to the event engine's next discrete boundary.
- [x] Localize sign-changing continuous roots by bisection and enqueue root metadata on the discrete event axis.
- [x] Add explicit upper-bound conservative uncertain-time scheduling and seeded independent-uniform Monte Carlo order estimates.
- [x] Add symbolic predicate expressions, bounded invariant checking and trace-label partial-order canonicalization.
- [x] Add HMAC-authenticated worker messages, SQLite WAL inbox/outbox, idempotent receipt, retry backoff and at-least-once handler processing.
- [x] Add subprocess termination testing between checkpoint generation and commit-pointer updates.
- [x] Expand CI across Linux, macOS and Windows hosted runners and publish benchmark reproduction artifacts from each OS (Python 3.12 matrix).

## Milestone 6 — replayable branching histories
- [x] Self-contained timeline-continuation schema v1 for completed discrete-event forks, independent of event-log schemas v1–v3.
- [x] Continuation schema v2 for event-boundary partial forks, including deterministic pending-queue capture and replay.
- [x] Fresh-process continuation replay and resume checks for history, pending queue, state digest, and scheduler snapshot digest.
- [x] Exact canonical JSON golden fixtures for continuation schemas v1 and v2.
- [ ] Record arbitrary external driver actions and continuous-integrator state as explicit continuation inputs.
- [ ] Validate continuation recovery under process interruption and filesystem-specific durability conditions beyond the existing event-log/checkpoint tests.

## Verification boundaries

The RK4 implementation is explicit and testable, but not suitable for stiff systems and not independently certified. Adaptive step-doubling estimates local truncation error; it is not a rigorous global error bound. Hybrid coupling stops at the next discrete boundary and localizes sign-changing roots by bisection; tangential root detection, dense output and certified solvers remain unimplemented.

Interval ordering expresses only what is guaranteed by closed intervals. Overlap does not imply simultaneity. Enumerated linear extensions are not probabilities; the separate Monte Carlo estimator assumes independent uniform timing errors. Bounded model checking has state, depth and path budgets; results apply only to the supplied transition relation and finite bounds.

CheckpointStore is a single-writer local-filesystem protocol. Unit corruption tests and process-termination tests do not prove power-loss durability across filesystems. Distributed causal reconciliation and authenticated worker transport are implemented, but the system is not consensus, exactly-once side effects or a production fault-tolerant cluster. Worker delivery is at-least-once; handlers must be idempotent. HMAC authenticates but does not encrypt unless TLS is configured. Partition ownership, membership epochs, leader election, and multi-node independent validation remain future work. Statistical bootstrap intervals do not eliminate systematic benchmark bias. Hosted-runner benchmark artifacts are reproducibility evidence, not independent third-party laboratory validation or universal performance claims.

Relativistic time dilation, quantum temporal models, closed timelike curves and other speculative physical ideas are not implemented. Physical predictions require explicit equations, units, assumptions, provenance and comparison with established reference results.
