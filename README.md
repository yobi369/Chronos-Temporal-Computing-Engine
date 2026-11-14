# Chronos Temporal Computing Engine

Chronos is an early-stage research software project for deterministic discrete-event simulation, causal event provenance, and branching logical timelines.

**Commercial product direction:** Chronos is being developed toward a Python-native environment for reproducible causal experiments, controlled timeline branching, and replay verification. See the [commercial product brief](docs/commercial-product-brief.md) for the proposed first offering, target users, validation programme, and launch gates. This is a product direction, not a claim that a polished commercial workbench or production service is already available.

## Implemented capabilities

- Deterministic discrete-event scheduling with stable time/sequence ordering.
- Event identity, logical time, causal-parent references, Lamport/vector clocks and declared causal graph.
- In-process snapshots and isolated timeline forks.
- Versioned snapshot JSON (v2) with documented in-memory migration from legacy v1.
- Canonical event-log JSON schemas v1, v2 and v3, with strict parsing and explicit version migrations.
- Schema-v3 initial-state capture, replay from recorded driver inputs, observed-history comparison and SHA-256 final-state digest checks.
- Bounded local event-log persistence using temporary-file writes, fsync and atomic replacement.
- Independent schema-v1/v2 fork continuation records with parent-checkpoint digests, branch-local inputs, partial-run pending queues, persistent replay, and final snapshot verification.
- Payload field contracts, malformed-file rejection, golden serialization fixtures and fresh-process replay tests.
- Hypothesis property tests and differential checks against a separate sorted-list reference scheduler.
- Finite-trace temporal operators and bounded explicit-state model checking.
- Reproducible experiment manifests and paired benchmark harness with cross-platform runner artifacts.
- Hybrid discrete/continuous RK4 integration with event-boundary stopping and bisection root localization.
- Conservative interval-time scheduling and seeded Monte Carlo event-order propagation.
- Symbolic state predicates and bounded invariant checking.
- HMAC-authenticated distributed worker messaging with durable SQLite inbox/outbox, retries and deduplication.
- Process-termination checkpoint recovery tests.

## Command-line interface

The chronos CLI validates and summarizes persisted event logs and timeline continuations without printing state or payload values. It can package validated artifacts into a portable report bundle, verify that bundle after transfer, and render a verified report as a self-contained offline HTML reviewer document.

    chronos --version
    chronos inspect-event-log path/to/event-log.json --json
    chronos inspect-continuation path/to/continuation.json --json
    chronos create-report --output-dir review-bundle --event-log path/to/event-log.json
    chronos verify-report review-bundle
    chronos render-report review-bundle

Use python -m chronos when invoking it from an environment where the console script is not on PATH. See [docs/cli.md](docs/cli.md) and [docs/experiment-reports.md](docs/experiment-reports.md) for commands, report structure, and verification boundaries.

## Development

    python -m pip install -e '.[dev]'
    ruff check .
    mypy src
    pytest --cov=chronos --cov-report=term-missing --cov-fail-under=70

Run the benchmark:

    python benchmarks/run_benchmarks.py --events 10000 --warmups 2 --repeats 7

See docs/reference-experiment.md for a replay-verified counterfactual supply-resilience workflow.

See [machine-readable serialization schemas](docs/schemas/README.md), docs/architecture.md, docs/event-logs-and-replay.md, docs/timeline-continuations.md, docs/event-log-migration.md, docs/temporal-model.md, docs/snapshot-format.md, docs/temporal-logic.md, docs/symbolic-verification.md, docs/hybrid-simulation.md, docs/uncertain-time.md, docs/distributed-execution.md, docs/checkpoint-recovery.md, docs/statistical-benchmarks.md, docs/validation.md, docs/research-roadmap.md, docs/market-readiness.md, and docs/competitive-positioning.md.

## Important limitations

Schema-v1 and schema-v2 event logs do not contain an initial-state record and therefore replay from an empty state. Migrating a historical non-empty run to v3 requires the exact original pre-dispatch state; Chronos cannot infer it. Replay requires deterministic handlers and explicitly recorded inputs. Hidden network, clock, random, environment, filesystem and global-state dependencies must be captured or controlled. Handler rollback cannot undo external effects, and replay is not a sandbox for untrusted handlers. Snapshots omit handlers. Digests are reproducibility checksums, not signatures or tamper-proof audit evidence. Event-log persistence is a bounded local single-writer file protocol, not a distributed event store.

Temporal evaluation uses finite-trace semantics; symbolic checking is explicit-state and bounded. Hybrid root localization detects sign changes only and rounds roots up to integer event ticks. Interval probability estimates assume independent uniform timing errors. Worker handlers are at-least-once and must be idempotent; HMAC does not encrypt traffic, so configure TLS for untrusted networks. The reference scheduler and benchmark are software baselines, not universal performance claims.

Chronos does not implement physical time travel, relativistic time manipulation, quantum temporal effects, or closed timelike curves. Such topics remain unimplemented research directions pending precise mathematical models and independent validation.

## License

Apache-2.0. See LICENSE.
