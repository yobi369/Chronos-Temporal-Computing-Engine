# Architecture

Chronos v0.1 is a deterministic, single-process, discrete-event simulator. Its temporal axis is an integer logical-time coordinate selected by each experiment. It is not a physical clock and does not model relativistic time dilation.

## Components

- Event: immutable event envelope with identity, logical timestamp, sequence, type, payload, and optional causal parent.
- LogicalClock: Lamport-style counter for ordering knowledge.
- SimulationEngine: priority-queue scheduler and handler dispatcher.
- EngineSnapshot: in-process checkpoint of queue, history, state, and counters.
- Timeline: named checkpoint that creates isolated branches.
- Validation: consistency checks over executed event logs.

Events execute by ascending (logical_time, sequence). The sequence is assigned at scheduling time, preserving insertion order for equal timestamps. Handlers receive (event, engine), may update state, and may schedule further events. Scheduled children inherit the current event as causal parent unless explicitly overridden. Handler code is not serialized; register compatible handlers on each fork.

A Timeline captures engine state. Each fork receives copied state, queue, and history. Branch mutations do not mutate the source engine or sibling branches.

## Limitations

Snapshots are in-process Python objects, not a stable persistence format. Payloads are not yet schema-validated. There is no distributed scheduler, crash recovery, formal causal inference, or physical-time model.
