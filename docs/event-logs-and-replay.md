# Event logs and deterministic replay

Chronos event-log schema version 1 stores two distinct sequences:

1. **Initial inputs** — events submitted by the experiment driver before execution.
2. **Observed history** — every event successfully executed, including events scheduled by handlers.

This distinction matters. Replaying every observed event as an initial input would duplicate handler-generated events. Replay therefore schedules only the recorded initial inputs, runs the registered handlers, and compares the resulting event history and final-state digest with the recorded observations.

## Canonical format

The JSON encoder sorts object keys, uses compact separators, emits UTF-8, and rejects non-finite numbers and non-JSON Python objects. The schema version is explicit. Unknown or missing object fields are rejected rather than silently ignored. A future incompatible format requires a new schema version and an explicit migration.

The final-state digest is SHA-256 over the canonical JSON representation of the engine's state dictionary. It is a reproducibility checksum, not a proof of semantic equivalence or tamper-proof provenance. Event-log files are not digitally signed.

## Capture and replay

    from chronos import SimulationEngine
    from chronos.event_log import EventInput, EventLog, replay_event_log, write_event_log

    engine = SimulationEngine("trial-001")

    def record(event, simulation):
        simulation.state["observations"] = (
            simulation.state.get("observations", 0) + event.payload["count"]
        )

    engine.register("record", record)
    inputs = (EventInput(5, "record", {"count": 2}),)
    for item in inputs:
        engine.schedule(item.time, item.event_type, item.payload)
    engine.run()

    log = EventLog.capture(engine, inputs)
    write_event_log("trial-001.chronos.json", log)

    # Re-register the same deterministic handler implementation.
    replayed = replay_event_log(log, {"record": record})
    assert replayed.state == engine.state

Handlers must be deterministic with respect to recorded inputs and explicitly controlled state. Hidden dependencies such as wall-clock time, network responses, random values, environment variables, mutable global state, or external files must be captured as inputs or controlled by the experiment. The replay API executes Python handlers; it is not a sandbox for untrusted code.

## Persistence limits

The writer stores to a temporary file in the destination directory and atomically replaces the target. The reader enforces a configurable byte limit before parsing. This is a local file format, not yet a multi-writer database, distributed event store, signed audit log, or crash-consistent checkpoint protocol.

## Verification boundary

A matching history and state digest show that a particular handler set reproduced a particular recorded run under the tested runtime and inputs. They do not establish physical time travel, quantum effects, relativistic predictions, or any other physical theory.
