# Contributing to Chronos

Thank you for helping improve Chronos Temporal Computing Engine.

Chronos is a Python research engine for deterministic discrete-event simulation, causal event provenance, versioned experiment histories, replay, and branching logical timelines. Contributions should preserve reproducibility, explicit semantics, and compatibility.

## Before opening a change

1. Check existing issues and pull requests for related work.
2. For changes affecting serialized data, public APIs, scheduler ordering, replay, persistence, or worker behavior, open or update an issue describing the invariant and compatibility impact.
3. Keep changes focused and reviewable.
4. Do not include credentials, private keys, customer data, or generated benchmark artifacts unless the task explicitly requires them.

## Development environment

- Python 3.11, 3.12, or 3.13
- Git
- A virtual environment is recommended

From the repository root:

```bash
python -m venv .venv
# Activate the environment using the command for your shell.
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## Required checks

Run the checks relevant to your change before requesting review:

```bash
ruff check .
mypy src
pytest --cov=chronos --cov-report=term-missing --cov-fail-under=70
python scripts/verify_distributions.py
python benchmarks/run_benchmarks.py --events 100 --warmups 0 --repeats 3
```

The CI workflow additionally runs the checks on Ubuntu, macOS, and Windows with Python 3.11, 3.12, and 3.13. Benchmark reproduction runs on the Python 3.12 jobs.

Report the exact commands and outcomes. Do not describe a check as passing if it was not run or if its workflow is still pending.

## Compatibility requirements

- Preserve event-log schemas v1, v2, and v3.
- Preserve snapshot schemas v1 and v2 and timeline-continuation schemas v1 and v2.
- Add a new versioned schema for incompatible wire-format changes; do not silently redefine a published schema.
- Preserve canonical golden fixtures unless an intentional, reviewed version change requires new fixtures.
- Add regression tests for bug fixes and tests for both successful and rejected inputs.
- Keep deterministic behavior independent of dictionary insertion order, wall-clock timing, network access, and unrecorded external state where the contract requires replayability.

## Scientific and operational scope

Do not describe Chronos as a physical time machine, a consensus system, an exactly-once execution platform, a certified numerical solver, or a production fault-tolerant cluster. Replay executes caller-registered handlers and is not a sandbox. Worker handlers have at-least-once processing semantics and must be idempotent or provide their own transactional safeguards.

Relativistic time dilation, quantum temporal effects, closed timelike curves, and physical time travel remain unimplemented research directions.

## Pull request expectations

A useful pull request includes:

- The problem and intended behavior.
- The design and compatibility impact.
- Tests added or updated.
- Exact local verification results.
- Known limitations and follow-up work.

Keep commits focused. Do not force-push shared branches or rewrite published history without explicit maintainer approval.
