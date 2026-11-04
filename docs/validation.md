# Validation strategy

Chronos is an early research prototype. Current validation targets software invariants, not physical theories.

Implemented tests cover stable scheduler ordering, rejection of past scheduling, causal-parent identity, unique event IDs and sequence numbers, branch state isolation, canonical event-log round trips, bounded local persistence, deterministic replay of explicit initial inputs, and final-state digest comparison.

Run tests with:

    python -m pip install -e '.[dev]'
    ruff check .
    mypy src
    pytest --cov=chronos --cov-report=term-missing

Planned validation: property-based scheduler tests; differential comparison with an independent reference scheduler; replay across supported Python versions; snapshot compatibility and migration tests; temporal-logic safety and liveness properties; queue stress tests; and bounded model-checking examples.

Replay assumes deterministic registered handlers and explicit initial inputs. It cannot make hidden network, clock, random, filesystem, environment, or global-state dependencies reproducible unless those dependencies are captured or controlled.

No software test result establishes a claim about the nature of physical time.
