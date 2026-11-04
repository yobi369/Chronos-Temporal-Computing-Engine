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
- Reproducible experiment manifests and a paired scheduler microbenchmark harness.

## Development

    python -m pip install -e '.[dev]'
    ruff check .
    mypy src
    pytest --cov=chronos --cov-report=term-missing

Run the benchmark:

    python benchmarks/run_benchmarks.py --events 10000 --warmups 2 --repeats 7

See docs/architecture.md, docs/temporal-model.md, docs/snapshot-format.md, docs/temporal-logic.md, docs/benchmarking.md, docs/validation.md, docs/event-logs-and-replay.md and docs/research-roadmap.md.

## Important limitations

Replay requires deterministic handlers and explicitly recorded inputs. Handler rollback cannot undo external effects. Snapshots omit handlers. Digests are not signatures or tamper-proof audit evidence. Temporal evaluation uses finite-trace semantics; bounded model checking is limited by the supplied transition relation, depth and state limit. The reference scheduler and benchmark are software baselines, not universal performance claims.

Chronos does not implement physical time travel, relativistic time manipulation, quantum temporal effects, or closed timelike curves. Such claims require precise mathematical models and independent validation.

## License

Apache-2.0. See LICENSE.
