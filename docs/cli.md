# Chronos command-line interface

The first Chronos command-line interface provides **read-only inspection and validation** of persisted event logs and timeline continuations. It does not execute event handlers, replay simulations, modify artifacts, or contact external services.

## Installation

Install Chronos in the active Python environment:

    python -m pip install chronos-temporal-computing-engine

For development from a repository checkout:

    python -m pip install -e '.[dev]'

The package exposes both the chronos executable and Python module entry point.

## Commands

Show the installed version:

    chronos --version
    python -m chronos --version

Inspect and validate an event log:

    chronos inspect-event-log path/to/event-log.json
    chronos inspect-event-log path/to/event-log.json --json

Inspect and validate a timeline continuation:

    chronos inspect-continuation path/to/continuation.json
    chronos inspect-continuation path/to/continuation.json --json

The default output is a human-readable metadata summary. The --json option emits a stable, machine-readable JSON object suitable for scripts and CI workflows.

## Reported metadata

Event-log inspection reports the schema version, timeline ID, initial-input and recorded-event counts, event-type counts, whether the initial state is captured, initial-state field names, declared payload contracts, and the recorded final-state digest.

Continuation inspection reports the schema version, parent and branch timeline IDs, parent history length, branch-input, recorded-event and pending-event counts, event types, checkpoint state field names, and recorded digests.

**Payload and state values are deliberately not printed.** Inspection reads and validates the artifact using Chronos' existing bounded persistence readers. It does not invoke handlers or replay the simulation.

## Exit behavior and trust boundary

A successful inspection exits with status 0. Invalid, unsupported, unreadable, or oversized artifacts produce a concise diagnostic on standard error and exit with status 2.

The SHA-256 digests are reproducibility checksums. They are not digital signatures, proof of authorship, or tamper-proof audit evidence. This CLI does not authenticate artifact provenance and must not be treated as a security boundary for untrusted files.
