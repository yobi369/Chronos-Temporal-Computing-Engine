# Architecture

Chronos v0.2 is a deterministic, single-process, discrete-event simulator. Its temporal axis is an integer logical-time coordinate selected by each experiment. It is not a physical clock and does not model relativistic time dilation.

## Components

- Event: frozen event envelope with identity, logical timestamp, sequence, type, payload, and optional causal parent. The dataclass is frozen, but nested payload objects are ordinary Python values and are not deeply immutable.
- LogicalClock: Lamport-style counter for ordering knowledge.
- SimulationEngine: priority-queue scheduler, handler dispatcher, and in-memory transaction boundary.
- EngineSnapshot: in-process checkpoint of queue, history, state, and counters.
- Timeline: named checkpoint that creates isolated branches.
- EventLog: versioned canonical JSON record of explicit inputs and observed execution history.
- Validation: consistency checks over executed event logs.

Events execute by ascending (logical_time, sequence). The sequence is assigned at scheduling time, preserving insertion order for equal timestamps. Handlers receive (event, engine), may update state, and may schedule further events. Scheduled children inherit the current event as causal parent unless explicitly overridden. Handler code is not serialized; register compatible handlers on each fork and during replay.

A Timeline captures engine state. Each fork receives copied state, queue, and history. Branch mutations do not mutate the source engine or sibling branches.

## Handler failure semantics

Each event step snapshots engine-managed state, the pending queue, sequence counter, logical clock, and current logical time before invoking a handler. If the handler raises, those engine-managed values are restored and the failed event remains pending for inspection or retry. This rollback cannot undo side effects outside the engine, such as network calls, file writes, messages sent to other processes, or mutations to external objects referenced by handlers. Handlers should therefore keep effects inside engine state or use an explicit idempotent/outbox design when integrating external systems.

## Event logs and replay

Version 1 event logs distinguish experiment-driver initial inputs from the complete observed history. Replay submits only the initial inputs, executes registered handlers, and compares the generated history and canonical final-state digest. The format is versioned and strict, with bounded local reads and atomic file replacement. It is not a database, a signed audit log, or a sandbox for untrusted handler code. See the event-log guide for usage and constraints.

## Limitations

Snapshots remain in-process Python objects without a migration policy. Event payloads are not deeply immutable. Hybrid integration is caller-driven and quantizes localized roots upward to integer event ticks. Uncertain-time scheduling uses a latest-bound policy. The worker transport provides HMAC-authenticated, durable at-least-once messages but not consensus or exactly-once effects. Symbolic checking is bounded explicit-state predicate evaluation.
