# Event logs and deterministic replay

Chronos event-log schema version 2 stores three related records:

1. **Initial inputs** — events submitted by the experiment driver before execution.
2. **Observed history** — every event successfully executed, including events scheduled by handlers.
3. **Payload contracts** — optional per-event-type object schemas that describe required and optional fields.

Schema version 1 remains readable and writable for existing logs. New captures use version 2. Version 1 has the same input/history structure but no embedded payload contracts. Unknown or missing fields are rejected within each supported version; a future incompatible format requires an explicit version and migration.

This distinction between inputs and observations matters. Replaying every observed event as an initial input would duplicate handler-generated events. Replay therefore schedules only the recorded initial inputs, runs the registered handlers, and compares the resulting event history and final-state digest with the recorded observations.

## Canonical format

Chronos canonical JSON is defined by this implementation's stable encoding rules:

- UTF-8 text, with object keys sorted lexicographically.
- Compact separators (comma and colon), with no insignificant whitespace.
- Only JSON-native values: null, booleans, integers, finite floats, strings, arrays, and objects with string keys.
- Non-finite numbers, non-string keys, tuples, custom objects, invalid UTF-8 text, and duplicate object keys are rejected rather than silently coerced.

This is a documented Chronos serialization contract, not a claim of full RFC 8785/JCS interoperability. Consumers that need cross-language digest agreement must implement and test these exact rules or adopt a separately specified canonicalization standard.

The final-state digest is SHA-256 over the canonical JSON representation of the engine's state dictionary. It is a reproducibility checksum, not a signature, semantic-equivalence proof, or tamper-proof provenance record. Event-log files are not digitally signed.

## Payload contracts

A `PayloadSchema` may be registered for each event type when capturing a log:

    from chronos import EventInput, EventLog, PayloadSchema

    schemas = {
        "credit": PayloadSchema(
            required={"account": "string", "amount": "number"},
            optional={"memo": "string"},
        )
    }

Supported property types are `null`, `boolean`, `integer`, `number`, `string`, `array`, and `object`. Boolean values are not accepted as integers or numbers. Additional properties are rejected by default; set `allow_additional_properties=True` only when the event contract intentionally permits them. When a non-empty schema registry is supplied, every initial and executed event type must have a schema, and both inputs and observed payloads are validated during serialization, parsing, and replay.

The schema registry is part of version-2 event-log data, so the contract travels with the recorded inputs. The schemas are deliberately a small object-validation subset, not a complete JSON Schema implementation.

## Capture and replay

    from chronos import (
        EventInput, EventLog, PayloadSchema, SimulationEngine,
        replay_event_log, write_event_log,
    )

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

    log = EventLog.capture(
        engine,
        inputs,
        payload_schemas={
            "record": PayloadSchema(required={"count": "integer"})
        },
    )
    write_event_log("trial-001.chronos.json", log)

    # Re-register the same deterministic handler implementation.
    replayed = replay_event_log(log, {"record": record})
    assert replayed.state == engine.state

Handlers must be deterministic with respect to recorded inputs and explicitly controlled state. Hidden dependencies such as wall-clock time, network responses, random values, environment variables, mutable global state, or external files must be captured as inputs or controlled by the experiment. The replay API executes Python handlers; it is not a sandbox for untrusted code.

## Persistence limits

The writer stores to a temporary file in the destination directory, flushes and fsyncs that file, then atomically replaces the target. A failed replacement leaves the previous target intact and removes the temporary file. The reader enforces a configurable byte limit before parsing. This is a local single-writer file operation, not a multi-writer database, distributed event store, signed audit log, or general power-loss durability guarantee. Filesystem and storage-controller behavior still require deployment-specific testing.

## Verification boundary

A matching history and state digest show that a particular handler set reproduced a particular recorded run under the tested runtime and inputs. They do not establish physical time travel, quantum effects, relativistic predictions, or any other physical theory.
