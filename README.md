# Chronos — Temporal Computing Engine

Chronos is an experimental, deterministic temporal-computing laboratory for event-driven systems, causal ordering, branching histories, counterfactual simulation, and reproducible replay.

The project treats speculative temporal ideas as **computational models**, not claims that physical time can be manipulated. Its first release focuses on a testable software foundation.

## Current status

Early research prototype. The initial implementation provides:

- A deterministic discrete-event scheduler with stable tie-breaking.
- Explicit event identity, logical time, and causal parent references.
- A Lamport-style logical clock utility.
- Immutable timeline forks from captured engine states.
- Event-log replay and integrity-oriented validation.
- Tests for ordering, causality, branching isolation, and deterministic execution.

Not implemented: relativistic spacetime simulation, quantum time models, physical time travel, distributed consensus, or production persistence. Those require separate mathematical specifications and validation.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
pytest
```

Run the example:

```bash
python examples/branching_timeline.py
```

## Design principles

1. **Determinism:** identical inputs and initial state produce identical event traces.
2. **Explicit causality:** causal links are represented, validated, and never inferred from wall-clock timestamps alone.
3. **Branch isolation:** a fork can explore an alternative future without mutating its parent.
4. **Reproducibility:** simulations expose their inputs, event traces, and configuration.
5. **Scientific honesty:** model assumptions and limits are documented; simulation output is not evidence of a physical phenomenon.

## Architecture

- `chronos.clock`: logical clock primitives.
- `chronos.events`: immutable event records.
- `chronos.engine`: deterministic discrete-event execution.
- `chronos.timeline`: forkable timeline snapshots.
- `chronos.validation`: event-log and causal consistency checks.

See [docs/architecture.md](docs/architecture.md), [docs/temporal-model.md](docs/temporal-model.md), and [docs/validation.md](docs/validation.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
