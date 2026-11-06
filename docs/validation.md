# Validation strategy

Chronos is an early-stage research prototype. Current validation targets software invariants, not physical theories.

## Implemented verification

The automated suite includes:
- stable scheduler ordering, rejection of past scheduling, causal-parent identity, unique event IDs and sequence numbers;
- isolated timeline forks and snapshot serialization, strict parsing, and legacy v1-to-v2 migration;
- canonical event-log round trips, payload-contract validation, bounded local persistence, atomic-replacement failure behavior, and schema migration;
- deterministic replay of explicit initial inputs, observed-history comparison, final-state digest comparison, randomized replay properties, and longer-history reproducibility;
- property-based scheduler checks and differential comparison with a separate sorted-list reference scheduler;
- causal graph and vector-clock behavior;
- finite-trace temporal operators, bounded symbolic checks, uncertain-time scheduling, hybrid integration and worker protocol behavior;
- process-termination checkpoint recovery and cross-platform benchmark smoke/reproduction workflows.

## Local development checks

Run from the repository root:

    python -m pip install -e '.[dev]'
    ruff check .
    mypy src
    pytest --cov=chronos --cov-report=term-missing --cov-fail-under=70
    python benchmarks/run_benchmarks.py --events 100 --warmups 0 --repeats 3

The GitHub Actions workflow runs the lint, type-check, coverage-enforced test suite, and benchmark smoke test on Ubuntu, macOS, and Windows with Python 3.11, 3.12, and 3.13. The independent benchmark reproduction and artifact upload are configured for the Python 3.12 matrix jobs.

## Remaining validation work

Further work includes broader cross-version serialized-fixture guarantees, multi-node independent implementations, membership and partition fault injection, additional numerical reference comparisons, and independent reproduction outside hosted CI. Checkpoint process-termination tests do not prove behavior under physical power loss, controller cache loss, or every filesystem and mount configuration.

Replay assumes deterministic registered handlers and explicit initial inputs. It cannot make hidden network, clock, random, filesystem, environment, or global-state dependencies reproducible unless those dependencies are captured or controlled.

No software test result establishes a claim about the nature of physical time.
