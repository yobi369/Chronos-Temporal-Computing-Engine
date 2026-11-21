"""Cooperative exclusive locks for local artifact writers."""
from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def exclusive_file_lock(
    destination: Path,
    *,
    error_factory: Callable[[str], Exception],
) -> Iterator[None]:
    """Reject overlapping Chronos writers with an atomic sidecar lock file.

    The lock is cooperative: it protects writers that use this helper. A hard
    process termination can leave a stale lock file, which must only be removed
    after an operator confirms that no writer for the destination is active.
    """
    lock_path = destination.with_name(f".{destination.name}.lock")
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
    except FileExistsError as exc:
        raise error_factory(
            f"writer lock already exists for {destination}; another writer may be active. "
            f"If it is stale, confirm no writer is running before removing {lock_path}"
        ) from exc

    try:
        lock_file = os.fdopen(descriptor, "w", encoding="ascii")
        descriptor = -1
        with lock_file:
            lock_file.write(f"pid={os.getpid()}\n")
            lock_file.flush()
            os.fsync(lock_file.fileno())
        yield
    finally:
        try:
            if descriptor >= 0:
                os.close(descriptor)
        finally:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
