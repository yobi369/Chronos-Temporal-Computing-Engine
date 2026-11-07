# Chronos Temporal Computing Engine

Chronos is an early-stage research software project for deterministic discrete-event simulation, causal event provenance, and branching logical timelines.

## Implemented capabilities

- Deterministic discrete-event scheduling with stable time/sequence ordering.
- Event identity, logical time, causal-parent references, Lamport/vector clocks and causal graph.
- In-process snapshots and isolated timeline forks.
- Versioned snapshot JSON (v2) with documented in-memory migration from legacy v1.
- Canonical event-log JSON, bounded local persistence, deterministic replay and final-state digest comparison.
- Hypothesis property tests and differential checks against a separate sorted-list reference scheduler.
- Finite-trace temporal operators and bounded explicit-state model checking.
- Reproducible experiment manifests and paired benchmark harness with cross-platform runner artifacts.
- Hybrid discrete/continuous RK4 integration with event-boundary stopping and bisection root localization.
- Conservative interval-time scheduling and seeded Monte Carlo event-order propagation.
- Symbolic state predicates and bounded invariant checking.
- HMAC-authenticated distributed worker messaging with durable SQLite inbox/outbox, retries and deduplication.
- Process-termination checkpoint recovery tests.

## Development

    python -m pip install -e '.[dev]'
    ruff check .
    mypy src
    pytest --cov=chronos --cov-report=term-missing

Run the benchmark:

    python benchmarks/run_benchmarks.py --events 10000 --warmups 2 --repeats 7

See docs/architecture.md, docs/temporal-model.md, docs/snapshot-format.md, docs/temporal-logic.md, docs/symbolic-verification.md, docs/hybrid-simulation.md, docs/uncertain-time.md, docs/distributed-execution.md, docs/checkpoint-recovery.md, docs/statistical-benchmarks.md and docs/research-roadmap.md.

## Important limitations

Replay requires deterministic handlers and explicitly recorded inputs. Handler rollback cannot undo external effects. Snapshots omit handlers. Digests are not signatures or tamper-proof audit evidence. Temporal evaluation uses finite-trace semantics; symbolic checking is explicit-state and bounded. Hybrid root localization detects sign changes only and rounds roots up to integer event ticks. Interval probability estimates assume independent uniform timing errors. Worker handlers are at-least-once and must be idempotent; HMAC does not encrypt traffic, so configure TLS for untrusted networks. The reference scheduler and benchmark are software baselines, not universal performance claims.

Chronos does not implement physical time travel, relativistic time manipulation, quantum temporal effects, or closed timelike curves. Such claims require precise mathematical models and independent validation.

## License

Apache-2.0. See LICENSE.
