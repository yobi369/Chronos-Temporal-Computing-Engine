# Validation strategy

Chronos is an early-stage research prototype. Current validation targets software invariants, not physical theories.

## Implemented verification

The automated suite includes:
- stable scheduler ordering, rejection of past scheduling, causal-parent identity, unique event IDs and sequence numbers;
- detached-copy boundaries for scheduled, dispatched, pending, and historical event payloads, preventing caller or handler mutation from silently rewriting engine-owned event records;
- isolated timeline forks and snapshot serialization, strict parsing, and legacy v1-to-v2 migration;
- canonical event-log round trips with exact golden serialization fixtures for schemas v1, v2 and v3; payload-contract validation; bounded local persistence; atomic-replacement failure behavior; strict malformed-file rejection; and explicit v1-to-v2 and v2-to-v3 migration;
- timeline-continuation schema v1/v2 round trips, parent-checkpoint and lineage digests, completed and event-boundary partial-fork replay, pending-queue tampering rejection, parent isolation, persistent reload, and fresh-process replay/resumption;
- deterministic replay from schema-v3 initial state and explicit inputs, observed-history comparison, final-state digest comparison, randomized replay properties, longer-history reproducibility, and a fresh-interpreter subprocess replay;
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

## Fork continuation verification

The continuation tests cover schema-v1 completed-fork compatibility and schema-v2 event-boundary partial forks. Partial records preserve the deterministic pending queue, and replay compares the inherited plus branch-local history, pending events, state digest, and full engine snapshot digest. A subprocess test reopens a partial continuation in a fresh interpreter, verifies the captured boundary, then resumes the remaining queue and compares the resulting digest and history length.

Schema v2 does not capture continuous-integrator state, arbitrary external driver calls interleaved with dispatch, or side effects outside engine-managed state. Those require explicit input and checkpoint semantics before they can be represented as deterministic continuation data.

## Remaining validation work

Further work includes broader cross-version serialized-fixture guarantees across additional Python implementations, multi-node independent implementations, membership and partition fault injection, additional numerical reference comparisons, and independent reproduction outside hosted CI. Checkpoint process-termination tests do not prove behavior under physical power loss, controller cache loss, or every filesystem and mount configuration.

Replay assumes deterministic registered handlers and explicit initial inputs. It cannot make hidden network, clock, random, filesystem, environment, or global-state dependencies reproducible unless those dependencies are captured or controlled. Event payload copies isolate engine-owned queue/history records, but individual Event payload objects remain mutable; tests do not claim deep immutability of arbitrary Python values.

No software test result establishes a claim about the nature of physical time.

## Constructor ownership regression tests

Focused tests now verify that EventInput detaches nested payloads, EventLog detaches caller-supplied input/event/state objects, and EngineSnapshot detaches caller-supplied queue payloads and state. These checks complement scheduler accessor isolation. They do not claim that nested dictionaries exposed from an already-constructed snapshot or event log are deeply immutable; the public contract continues to require treating captured records as read-only.

