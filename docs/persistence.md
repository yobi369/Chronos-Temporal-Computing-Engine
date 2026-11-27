# Local artifact persistence protocol

Chronos persists event logs and timeline continuations as versioned canonical JSON files. This protocol is intended for cooperative writers on a local filesystem. It is not an append-only journal, a multi-writer database, a distributed event store, or a consensus protocol.

## Writer exclusion

Before replacing a destination, the event-log and continuation writers create a sibling sidecar lock named `.<destination-name>.lock` using exclusive file creation (`O_CREAT | O_EXCL`). The lock records the creating process ID and a per-acquisition owner marker. The lock is held while the writer creates and fsyncs a same-directory temporary file and atomically replaces the destination.

On normal release, Chronos checks both the sidecar's file identity and its owner marker before removing it. The check uses a bounded read and refuses to follow symlinks or block on special files. If lock initialization itself fails after creating an empty or partially written sidecar, cleanup removes it only when the path still identifies the file created by that acquisition. If the initial file-identity check (`fstat`) fails, Chronos closes the descriptor but leaves the sidecar for explicit operator inspection: without the descriptor identity, it cannot safely prove that the path still names the file created by that acquisition. These checks avoid deleting a replacement lock if an operator or external process removed and recreated the path while the original writer was active. They are defensive checks, not a hostile-process security boundary or a substitute for leaving active locks untouched.

If the lock already exists, a competing Chronos writer fails immediately with an event-log or continuation validation error. It does not wait, overwrite the lock, or automatically assume that the owner is dead. Callers that want retry behavior must implement bounded retry/backoff outside the persistence API.

The lock is cooperative. It coordinates processes that use these Chronos writers; it is not a security boundary against another local process that deliberately removes or replaces the lock file. Filesystem semantics, especially on network or unusual filesystems, must be validated for the deployment environment.

## Interrupted writers and stale locks

A normal Python exception releases the lock and removes the temporary file. A hard process termination can leave both a sidecar lock and a temporary file behind.

Chronos deliberately does not remove a pre-existing lock automatically. An operator must:

1. inspect the lock file and its recorded PID;
2. confirm that no process is still writing the destination (accounting for PID reuse and the host's process namespace);
3. only then remove the stale `.<destination-name>.lock` file;
4. after the stale lock is removed, use the explicit cleanup API below if abandoned temporary files need removal. Do not delete a lock merely because a write appears slow. Removing a live lock would permit overlapping replacements and defeat the single-writer guarantee.

## Explicit stale-temporary-file cleanup

`cleanup_stale_temporary_files(path, minimum_age_seconds=86_400)` is an operator-invoked recovery helper exported from `chronos`. It is **never** called automatically by event-log or continuation readers/writers. It acquires the same destination sidecar lock and fails closed if a lock already exists. It considers only regular files named `.<destination-name>.*.tmp` whose modification time is at least the requested age; symlinks, directories, fresh files, and unrelated names are ignored. The default minimum age is 24 hours, and the function returns the sorted tuple of removed filenames.

Use it only after inspecting the stale lock, confirming its PID is no longer writing, and manually removing that stale lock. The helper does not remove locks. The lock coordinates Chronos writers only: do not run cleanup while a non-Chronos process may be using the same temporary-file naming convention in that directory. If directory fsync fails after unlinking, files may already be gone even though the helper raises; inspect the directory before retrying.

## Atomic replacement and durability boundary

The writer encodes and validates the complete canonical JSON document before writing. It creates the temporary file in the destination directory, writes the bytes, flushes and fsyncs the temporary file, then uses `os.replace` to replace the destination. On POSIX platforms it next opens and fsyncs the containing directory before releasing the writer lock. Windows skips this directory-sync step because Python's standard library does not provide a portable directory-handle fsync there.

A failure before `os.replace` preserves the previous destination and removes the temporary file. A directory-fsync failure occurs **after** replacement: the writer raises the underlying `OSError`, but the destination may already contain the new complete document. Callers must inspect/read the destination before retrying rather than assuming the write was rolled back. The lock is released in either case.

Directory fsync improves persistence of the rename on supported POSIX filesystems, but it does not establish universal power-loss durability. Storage-controller caches, filesystem and mount behavior, virtualized storage, and platform-specific guarantees still require deployment-specific testing. No physical power-loss guarantee is claimed.

Readers enforce a configurable byte limit before parsing and validate UTF-8, canonical JSON constraints, schema version, payload contracts, and event-history structure. Readers do not take the writer lock: same-directory replacement is intended to let them observe either the previous complete file or the new complete file on filesystems that provide the expected replacement semantics.

## Compatibility and trust

Writer locking does not change event-log schemas v1/v2/v3, snapshot schemas v1/v2, timeline-continuation schemas v1/v2, canonical JSON bytes, or digest inputs. It does not turn SHA-256 state digests into signatures or authenticity proofs. Event replay still executes caller-registered Python handlers and is not a sandbox.

## Verification

The focused persistence tests exercise an overlapping writer attempt at the replacement boundary for both event logs and timeline continuations, lock cleanup after simulated replacement failures, directory-fsync ordering, and post-replacement error handling. A subprocess test holds a real lock while a second process attempts a write, then terminates the holder and verifies that the stale lock blocks writes until it is manually removed. Explicit cleanup tests cover age filtering, exact destination matching, symlink/directory exclusion, active-lock rejection, deterministic results, and post-unlink directory-sync errors. The lock-helper tests also verify that a releasing owner does not remove a replacement sidecar, that failed `fdopen` or partial marker writes do not strand an empty/partial lock, that a failed initial `fstat` closes its descriptor and leaves the sidecar fail-closed for operator inspection, and that a replacement symlink is not followed or removed. Filesystem-specific power-loss behavior remains separate work.
