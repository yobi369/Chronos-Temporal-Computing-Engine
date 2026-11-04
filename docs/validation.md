# Validation strategy

Chronos is an early research prototype. Current validation targets software invariants, not physical theories.

Implemented tests cover stable scheduler ordering, rejection of past scheduling, causal-parent identity, unique event IDs and sequence numbers, and branch state isolation.

Run tests with:

    python -m pip install -e '.[dev]'
    pytest

Planned validation: property-based scheduler tests; differential comparison with an independent reference scheduler; deterministic replay from canonical inputs; temporal-logic safety and liveness properties; queue stress tests; and bounded model-checking examples.

No software test result establishes a claim about the nature of physical time.
