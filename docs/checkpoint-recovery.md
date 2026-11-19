# Checkpoint persistence and crash recovery

CheckpointStore writes immutable generation documents, flushes and fsyncs the file, atomically replaces the generation path, then atomically replaces the CURRENT commit pointer. Recovery follows CURRENT and validates generation metadata and SHA-256 content integrity. The store is single-writer per directory.

The subprocess crash suite terminates a child process at four commit boundaries: before the new generation is replaced, after the generation replacement, immediately before the CURRENT pointer replacement, and immediately after the pointer replacement. Recovery must select the previous committed generation for the first three cases and the new committed generation for the last case. This tests the old-or-new commit invariant rather than merely testing that a JSON file can be reopened.

CI runs this suite on Linux, macOS and Windows hosted runners. These provide cross-OS coverage over the runners' local filesystems, but they are not a controlled filesystem laboratory: mount types and storage configuration are not asserted by the workflow.

This test covers process termination, not actual power loss, controller write-cache loss, network filesystem semantics, or every filesystem. Atomic replacement and directory fsync guarantees vary by platform and mount. Windows skips directory fsync where opening directories for fsync is unsupported. Production durability still requires validation on the exact target filesystem, storage stack, mount options and deployment environment.
