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
- TimelineContinuation: independent schema-v1/v2 record of a fork boundary. V1 covers completed forks; v2 also records the deterministic pending queue at an event-boundary partial run.
- Validation and causal analysis: consistency checks over executed event logs and queries over declared event-parent provenance.

Events execute by ascending (logical_time, sequence). The sequence is assigned at scheduling time, preserving insertion order for equal timestamps. Handlers receive (event, engine), may update state, and may schedule further events. Scheduled children inherit the current event as causal parent unless explicitly overridden. Handler code is not serialized; register compatible handlers on each fork and during replay.

A Timeline captures engine state. Each fork receives copied state, queue, and history. Branch mutations do not mutate the source engine or sibling branches. Snapshot files omit handler functions; applications must register compatible handlers after restoration.

## Handler failure semantics

Each event step snapshots engine-managed state, the pending queue, sequence counter, logical clock, and current logical time before invoking a handler. If the handler raises, those engine-managed values are restored and the failed event remains pending for inspection or retry. This rollback cannot undo side effects outside the engine, such as network calls, file writes, messages sent to other processes, or mutations to external objects referenced by handlers. Handlers should therefore keep effects inside engine state or use an explicit idempotent/outbox design when integrating external systems.

## Event logs and replay

Event-log schema v3 records the engine state immediately before the first dispatched event, experiment-driver initial inputs, the complete observed execution history, and optional payload field contracts. Strict schema-v1 and schema-v2 readers and writers remain supported: v1 has no payload contracts or initial state; v2 adds payload contracts but no initial state; v3 adds initial state. The v1-to-v2 and v2-to-v3 upgrades are explicit migrations. The v2-to-v3 migration requires the caller to supply the original pre-dispatch state because it cannot be inferred from historical events or the final digest.

Replay schedules only recorded initial inputs, restores the recorded initial state, executes registered deterministic handlers, and compares generated history and the canonical final-state digest. Canonical serialization rejects unsupported Python values, duplicate JSON keys, non-finite numbers, and unknown schema fields. Persistence uses bounded local reads and temporary-file writes followed by fsync and atomic replacement. The digest is a reproducibility checksum, not a signature or tamper-proof audit record. See the event-log guide and migration guide for details.

## Fork continuation and replay

Event-log schema v3 models a run from its initial state; it does not by itself model a branch that inherits a populated checkpoint, pending queue, history, and scheduler counters. TimelineContinuation uses an independent schema so fork replay can evolve without changing event-log compatibility.

Continuation schema v1 remains readable and writable for completed discrete-event forks. Schema v2 adds a deterministic pending-event queue and supports a branch stopped at an event boundary, including a zero-dispatch boundary or a handler that has scheduled follow-up events. Both versions embed the exact parent snapshot-v2 checkpoint, record parent history/state/checkpoint digests, retain only branch-local driver inputs and the observed history suffix, and verify the final state digest plus the complete engine-snapshot digest. V2 additionally compares the reconstructed pending queue.

Replay recreates the child checkpoint using the same construction as Timeline.fork, restores inherited history and pending events, registers caller-supplied handlers, schedules the recorded branch inputs, and dispatches exactly the recorded history-suffix length. The parent checkpoint and sibling timelines are not mutated. The continuation guide documents the canonical format, persistence API, version compatibility, and replay checks.

The continuation format represents a fixed set of branch-local inputs and deterministic handler-generated events. It does not persist an arbitrary stream of external driver API calls interleaved with dispatch. Capture rejects a changed pre-dispatch state and logical-time advancement not represented by dispatched events. Schema v2 does not capture continuous-integrator state, hidden wall-clock/network/random dependencies, or external side effects. Handlers must be deterministic with respect to the recorded inputs and controlled state.

## Distributed workers

The worker protocol provides HMAC-authenticated messages and acknowledgements, size-bounded framing, durable SQLite WAL inbox/outbox storage, deduplication, retries, and at-least-once handler processing. HMAC does not encrypt traffic; TLS must be configured on untrusted networks. This protocol does not provide consensus, membership epochs, leader election, partition ownership, or exactly-once side effects. See the distributed execution guide.

## Limitations

Event payloads are not deeply immutable. Hybrid integration uses explicit RK4 methods for non-stiff ODEs and quantizes localized sign-changing roots upward to integer ticks; tangential-root detection and certified solvers are not implemented. Uncertain-time scheduling uses a declared latest-bound policy; its Monte Carlo estimates assume independent uniform timing errors. Symbolic checking is bounded explicit-state exploration over caller-supplied transitions. Checkpoint persistence is a single-writer local-filesystem protocol, not a general database or universal power-loss guarantee.

Relativistic time dilation, quantum temporal models, closed timelike curves, and physical time travel are unimplemented research directions. No physical predictions are claimed.
