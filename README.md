# Chronos — Temporal Computing Engine

Chronos is an experimental, deterministic temporal-computing laboratory for event-driven systems, causal ordering, branching histories, counterfactual simulation, and reproducible experiments.

The project treats speculative temporal ideas as computational models, not claims that physical time can be manipulated.

## Current status

Early research prototype. The initial implementation provides:

- A deterministic discrete-event scheduler with stable tie-breaking.
- Explicit event identity, logical time, and declared causal-parent references.
- Lamport and vector clocks for logical ordering and distributed happens-before analysis.
- A causal provenance graph with ancestor and descendant queries.
- In-process timeline snapshots and isolated forks.
- Event-log consistency validation.
- Tests for ordering, causal provenance, bounded execution, and branch isolation.

Not implemented: persistent replay, relativistic spacetime simulation, quantum time models, physical time travel, distributed consensus, or production persistence. These require separate mathematical specifications and validation.

## Quick start

Requires Python 3.11+.

    python -m pip install -e ".[dev]"
    pytest

Run the example:

    python examples/branching_timeline.py

## Design principles

1. Determinism: identical inputs and initial state produce identical event traces.
2. Explicit causality: causal links are declared and validated, not inferred from wall-clock timestamps.
3. Branch isolation: a fork explores an alternative future without mutating its parent.
4. Reproducibility: experiments expose their inputs, event traces, and configuration.
5. Scientific honesty: model assumptions and limits are documented; simulation output is not evidence of a physical phenomenon.

## Architecture

- `chronos.clock`: logical clock primitives.
- `chronos.events`: immutable event records.
- `chronos.engine`: deterministic discrete-event execution.
- `chronos.timeline`: forkable in-process snapshots.
- `chronos.validation`: event-log consistency checks.

See [docs/architecture.md](docs/architecture.md), [docs/temporal-model.md](docs/temporal-model.md), and [docs/validation.md](docs/validation.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
