# Chronos Temporal Computing Engine

Chronos is an early-stage research software project for deterministic discrete-event simulation, causal event provenance, and branching logical timelines.

## Implemented capabilities

- Deterministic discrete-event scheduling with stable time/sequence ordering.
- Explicit event identity, logical time, and declared causal-parent references.
- Lamport and vector clocks for logical ordering and happens-before analysis.
- Causal provenance graph with ancestor and descendant queries.
- In-process snapshots and isolated timeline forks.
- Event-log consistency validation.
- Canonical versioned event-log JSON, bounded local persistence, deterministic replay from explicit initial inputs, and final-state digest comparison.

## Development

    python -m pip install -e '.[dev]'
    ruff check .
    mypy src
    pytest --cov=chronos --cov-report=term-missing

See the [architecture](docs/architecture.md), [temporal model](docs/temporal-model.md), [validation strategy](docs/validation.md), [event logs and replay](docs/event-logs-and-replay.md), and [research roadmap](docs/research-roadmap.md).

## Important limitations

Replay requires deterministic handlers and explicitly recorded initial inputs. It does not sandbox imported code, capture arbitrary external dependencies, provide a distributed database, or guarantee crash-consistent checkpoints. Event-log state digests are reproducibility checksums, not signatures or tamper-proof audit evidence.

Chronos does not implement physical time travel, relativistic time manipulation, quantum temporal effects, or closed timelike curves. These remain speculative research directions unless and until precise mathematical models and independent validation are supplied.

## License

Apache-2.0. See [LICENSE](LICENSE).
