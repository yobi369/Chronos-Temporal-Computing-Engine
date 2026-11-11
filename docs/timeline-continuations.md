# Timeline continuations and fork replay

Chronos event-log schema v3 records a run that starts from an initial state and explicit driver inputs. A fork is different: it begins from a checkpoint that may already contain executed history, pending events, a non-zero logical clock, and a sequence counter. Replaying only the fork's new inputs from an empty engine would lose that context or execute inherited events incorrectly.

## Independent continuation format

TimelineContinuation uses its own schema version 1. It does not change or replace event-log schemas v1–v3. A continuation record contains:

- the parent timeline ID and the fork's timeline ID;
- the complete parent EngineSnapshot in the existing snapshot-v2 format;
- the parent history length, history digest, state digest, and full checkpoint digest;
- only the new driver inputs scheduled on the fork;
- the observed history suffix produced after the checkpoint;
- the final state digest and final engine-snapshot digest.

The embedded checkpoint is self-contained. The parent history is retained once inside the snapshot; the continuation stores only the appended history suffix. The checkpoint digest covers the parent timeline ID, logical time, pending queue, history, state, sequence counter, and logical-clock value. The separate history and state digests make the lineage boundary explicit and independently checkable.

## Capture, persistence, and replay

A completed fork can be recorded as follows:

    from chronos import (
        EventInput,
        Timeline,
        capture_timeline_continuation,
        replay_timeline_continuation,
        write_timeline_continuation,
    )

    checkpoint = Timeline.capture("baseline", parent_engine)
    branch = checkpoint.fork("scenario-a", handlers=handlers)
    branch_inputs = (EventInput(8, "credit", {"amount": 5}),)

    for item in branch_inputs:
        branch.schedule(item.time, item.event_type, item.payload)
    branch.run()

    record = capture_timeline_continuation(
        checkpoint, branch, branch_inputs
    )
    write_timeline_continuation("scenario-a.chronos.json", record)

    # Register the same deterministic handlers in the replaying process.
    replayed = replay_timeline_continuation(record, handlers)

Replay recreates the child checkpoint using the same fork-snapshot construction as Timeline.fork, restores inherited pending events and history, schedules only the branch-local inputs, and runs the deterministic handlers. It verifies the complete resulting history, final state digest, and final snapshot digest. The snapshot digest also checks scheduler counters, logical time, queue state, and logical-clock state—not only the simulation's application data.

The format has strict fields and canonical JSON encoding. Reads are size-bounded; writes use a temporary file, fsync, and atomic replacement. The continuation schema is versioned independently so its evolution does not silently alter the event-log v1/v2/v3 compatibility contract.

## Capture boundary

Schema v1 deliberately records **completed discrete-event continuations only**. Capture rejects a branch if:

- its inherited parent history is not an exact prefix;
- the branch's pre-dispatch state differs from the parent checkpoint state;
- pending events remain;
- logical time was manually or continuously advanced beyond the final dispatched event.

A partial run needs an explicit run-boundary/continuation protocol before it can be replayed faithfully. Continuous integrator state and external mutations are not inferred from a discrete event history. Applications should represent external changes as recorded events and keep handlers deterministic with respect to recorded inputs.

## Trust and scientific scope

The embedded snapshot and digests provide reproducibility and consistency checks, not cryptographic authenticity. Records are not signed or encrypted, and replay executes caller-registered Python handlers; it is not a sandbox for untrusted code. Handlers must not depend on hidden wall-clock, network, random, environment, or external-file state unless those dependencies are captured as explicit inputs.

Timeline continuations describe branching in Chronos's experiment-defined discrete logical-time model. They do not implement physical time travel, relativistic time dilation, quantum temporal models, or closed timelike curves. Those remain unimplemented research directions.
