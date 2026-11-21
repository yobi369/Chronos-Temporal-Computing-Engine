# Local artifact persistence protocol

Chronos persists event logs and timeline continuations as versioned canonical JSON files. This protocol is intended for cooperative writers on a local filesystem. It is not an append-only journal, a multi-writer database, a distributed event store, or a consensus protocol.

## Writer exclusion

Before replacing a destination, the event-log and continuation writers create a sibling sidecar lock named `.<destination-name>.lock` using exclusive file creation (`O_CREAT | O_EXCL`). The lock records the creating process ID. The lock is held while the writer creates and fsyncs a same-directory temporary file and atomically replaces the destination.

If the lock already exists, a competing Chronos writer fails immediately with an event-log or continuation validation error. It does not wait, overwrite the lock, or automatically assume that the owner is dead. Callers that want retry behavior must implement bounded retry/backoff outside the persistence API.

The lock is cooperative. It coordinates processes that use these Chronos writers; it is not a security boundary against another local process that deliberately removes or replaces the lock file. Filesystem semantics, especially on network or unusual filesystems, must be validated for the deployment environment.

## Interrupted writers and stale locks

A normal Python exception releases the lock and removes the temporary file. A hard process termination can leave both a sidecar lock and a temporary file behind.

Chronos deliberately does not remove a pre-existing lock automatically. An operator must:

1. inspect the lock file and its recorded PID;
2. confirm that no process is still writing the destination (accounting for PID reuse and the host's process namespace);
3. only then remove the stale `.<destination-name>.lock` file;
4. inspect and remove abandoned `.<destination-name>.*.tmp` files only after confirming they are not active writer files.

Do not delete a lock merely because a write appears slow. Removing a live lock would permit overlapping replacements and defeat the single-writer guarantee.

## Atomic replacement and durability boundary

The writer encodes and validates the complete canonical JSON document before writing. It creates the temporary file in the destination directory, writes the bytes, flushes and fsyncs the temporary file, then uses `os.replace` to replace the destination. A normal replacement failure preserves the previous destination and removes the temporary file; the lock is then released.

The current protocol does **not** fsync the containing directory after replacement. It therefore does not claim that the rename is durable across every power-loss scenario, storage-controller cache, filesystem, mount option, or operating system. The exact guarantees of `os.replace`, file fsync, and directory metadata persistence must be tested on the target filesystem. Additional directory-fsync and crash-recovery work remains a release-readiness item.

Readers enforce a configurable byte limit before parsing and validate UTF-8, canonical JSON constraints, schema version, payload contracts, and event-history structure. Readers do not take the writer lock: same-directory replacement is intended to let them observe either the previous complete file or the new complete file on filesystems that provide the expected replacement semantics.

## Compatibility and trust

Writer locking does not change event-log schemas v1/v2/v3, snapshot schemas v1/v2, timeline-continuation schemas v1/v2, canonical JSON bytes, or digest inputs. It does not turn SHA-256 state digests into signatures or authenticity proofs. Event replay still executes caller-registered Python handlers and is not a sandbox.

## Verification

The focused persistence tests exercise an overlapping writer attempt at the replacement boundary for both event logs and timeline continuations, plus lock cleanup after a simulated replacement failure. The full CI matrix is required before treating this change as verified. Process-kill stale-lock recovery, directory fsync, and filesystem-specific power-loss behavior remain separate work.
