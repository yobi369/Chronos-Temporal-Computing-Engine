# Durable checkpoint generations and recovery

CheckpointStore writes canonical JSON generations with SHA-256 integrity checks, fsyncs the temporary file, atomically replaces the generation file, then atomically advances CURRENT and fsyncs the directory. Recovery follows CURRENT and validates schema, generation and checksum before returning payload.

This is a single-writer local-filesystem protocol. Atomic rename and directory fsync guarantees vary by filesystem and platform. It does not provide multi-process locking, replicated durability, WAL transactions, automatic engine serialization, or recovery from media loss. Store a snapshot_to_json document or another JSON-compatible payload. Crash testing should terminate a child process at write boundaries on each target filesystem; unit corruption tests do not substitute for power-loss testing.
