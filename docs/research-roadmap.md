# Research and engineering roadmap

A completed software milestone is not evidence for a physical theory.

## Milestone 1 — deterministic temporal core
- [x] Deterministic discrete-event scheduler.
- [x] Event-parent provenance, Lamport and vector clocks.
- [x] In-process snapshots, timeline forks, causal graph, initial tests and CI.

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
- [ ] Authenticated transport, durable inbox/outbox, retries and idempotent side-effect handling.
- [ ] Partition ownership, membership epochs, concurrent state conflict policy and distributed fault injection.
- [ ] Multi-node independent implementation and network-partition testing.

## Milestone 5 — integrated hybrid, uncertainty and worker execution
- [x] Couple RK4 integration to the event engine's next discrete boundary.
- [x] Localize sign-changing continuous roots by bisection and enqueue exact root metadata on the discrete event axis.
- [x] Add explicit upper-bound conservative uncertain-time scheduling and seeded independent-uniform Monte Carlo order estimates.
- [x] Add symbolic predicate expressions, bounded invariant checking and trace-label partial-order canonicalization.
- [x] Add HMAC-authenticated worker messages, SQLite WAL inbox/outbox, idempotent receipt, retry backoff and at-least-once handler processing.
- [x] Add subprocess termination testing between checkpoint generation and commit-pointer updates.
- [x] Expand CI across Linux, macOS and Windows hosted runners and publish benchmark reproduction artifacts from each OS.

## Verification boundaries
The RK4 implementation is explicit and testable, but not suitable for stiff systems and not independently certified. Adaptive step-doubling estimates local truncation error; it is not a rigorous global error bound. Hybrid coupling now stops at the next discrete boundary and localizes sign-changing roots by bisection; tangential root detection, dense output and certified solvers remain unimplemented.

Interval ordering expresses only what is guaranteed by closed intervals. Overlap does not imply simultaneity, and enumerated orders are not probabilities. Bounded model checking has state, depth and path budgets; results apply only to the supplied transition relation and finite bounds.

CheckpointStore is a single-writer local-filesystem protocol. Unit corruption tests do not prove power-loss durability across filesystems. Distributed reconciliation is a batch merge protocol, not consensus, transport, exactly-once execution or a production cluster. Statistical bootstrap intervals do not eliminate systematic benchmark bias. Independent multi-machine reproduction remains a required research activity.

Relativistic time dilation, quantum temporal models, closed timelike curves and other speculative physical ideas are not implemented. Physical predictions require explicit equations, units, assumptions, provenance and comparison with established reference results.


The integrated hybrid API currently uses integer discrete ticks and real-valued continuous coordinates. A localized root is rounded upward to the next integer tick while its exact time/state remain in the payload. Sign-change detection does not detect tangential roots. Uncertain scheduler execution uses an explicit latest-bound policy; probability propagation assumes independent uniform draws and is not Bayesian inference. Symbolic predicates are evaluated over explicit finite states, not a BDD/SAT solver; partial-order trace canonicalization is only sound when the caller's independence relation is valid. Worker delivery is authenticated with HMAC but is not encrypted unless TLS is configured; inbox handlers are at-least-once and must be idempotent. Hosted CI runs are independent runner VMs, not independent third-party laboratories or filesystems.