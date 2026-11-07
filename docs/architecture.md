# Architecture

Chronos v0.5.0 is an early-stage research software project for deterministic, single-process discrete-event simulation, causal event provenance, and branching logical timelines. Its temporal axis is an integer logical-time coordinate selected by each experiment. It is not a physical clock and does not model relativistic time dilation.

## Components

- Event: frozen event envelope with identity, logical timestamp, sequence, type, payload, and optional causal parent. The dataclass is frozen, but nested payload objects are ordinary Python values and are not deeply immutable.
- LogicalClock: Lamport-style counter for ordering knowledge.
- VectorClock: distributed happens-before observations; concurrent vectors are incomparable under the vector-clock relation.
- SimulationEngine: priority-queue scheduler, handler dispatcher, and in-memory transaction boundary.
- EngineSnapshot: in-process checkpoint of queue, history, state, and counters.
- Snapshot I/O: versioned JSON snapshot format (v2), with an explicit in-memory migration from legacy flat v1.
- Timeline: named checkpoint that creates isolated branches.
- EventLog: versioned canonical JSON record of explicit inputs, observed execution history, and optional payload contracts.
- Validation and causal analysis: consistency checks over executed event logs and queries over declared event-parent provenance.

Events execute by ascending (logical_time, sequence). The sequence is assigned at scheduling time, preserving insertion order for equal timestamps. Handlers receive (event, engine), may update state, and may schedule further events. Scheduled children inherit the current event as causal parent unless explicitly overridden. Handler code is not serialized; register compatible handlers on each fork and during replay.

A Timeline captures engine state. Each fork receives copied state, queue, and history. Branch mutations do not mutate the source engine or sibling branches. Snapshot files omit handler functions; applications must register compatible handlers after restoration.

## Handler failure semantics

Each event step snapshots engine-managed state, the pending queue, sequence counter, logical clock, and current logical time before invoking a handler. If the handler raises, those engine-managed values are restored and the failed event remains pending for inspection or retry. This rollback cannot undo side effects outside the engine, such as network calls, file writes, messages sent to other processes, or mutations to external objects referenced by handlers. Handlers should therefore keep effects inside engine state or use an explicit idempotent/outbox design when integrating external systems.

## Event logs and replay

Event-log schema v2 separates experiment-driver initial inputs from the complete observed execution history and can carry payload field contracts. Schema v1 remains readable and has an explicit migration helper. Replay schedules only recorded initial inputs, executes registered deterministic handlers, and compares the generated history and canonical final-state digest. The format uses documented canonical JSON rules, bounded local reads, and atomic file replacement. The digest is a reproducibility checksum, not a signature or tamper-proof audit record. See the event-log guide and migration guide for details.

## Distributed workers

The worker protocol provides HMAC-authenticated messages and acknowledgements, size-bounded framing, durable SQLite WAL inbox/outbox storage, deduplication, retries, and at-least-once handler processing. HMAC does not encrypt traffic; TLS must be configured on untrusted networks. This protocol does not provide consensus, membership epochs, leader election, partition ownership, or exactly-once side effects. See the distributed execution guide.

## Limitations

Event payloads are not deeply immutable. Hybrid integration uses explicit RK4 methods for non-stiff ODEs and quantizes localized sign-changing roots upward to integer ticks; tangential-root detection and certified solvers are not implemented. Uncertain-time scheduling uses a declared latest-bound policy; its Monte Carlo estimates assume independent uniform timing errors. Symbolic checking is bounded explicit-state exploration over caller-supplied transitions. Checkpoint persistence is a single-writer local-filesystem protocol, not a general database or universal power-loss guarantee.

Relativistic time dilation, quantum temporal models, closed timelike curves, and physical time travel are unimplemented research directions. No physical predictions are claimed.
