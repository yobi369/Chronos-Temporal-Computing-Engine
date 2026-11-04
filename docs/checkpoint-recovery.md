# Checkpoint persistence and crash recovery

CheckpointStore writes immutable generation documents, flushes and fsyncs the file, atomically replaces the generation path, then atomically replaces the CURRENT commit pointer. Recovery follows CURRENT and validates generation metadata and SHA-256 content integrity. The store is single-writer per directory.

The subprocess crash test exits immediately after writing a new generation but before updating CURRENT. Recovery must continue to load the previously committed generation. CI exercises this path on Linux, macOS and Windows hosted runners.

This test covers a process termination boundary, not actual power loss, controller write-cache loss, network filesystem semantics, or every filesystem. Atomic replacement and directory fsync guarantees vary by platform and mount. Windows skips directory fsync where opening directories for fsync is unsupported. Production durability still requires validation on the target filesystem, storage stack and deployment environment.
