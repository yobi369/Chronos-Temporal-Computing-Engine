"""Cooperative exclusive locks for local artifact writers."""
from __future__ import annotations

import os
import secrets
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
    The owner marker also prevents a normal lock release from deleting a
    different lock file that replaced this acquisition's sidecar.
    """
    lock_path = destination.with_name(f".{destination.name}.lock")
    owner_contents = f"pid={os.getpid()}\nowner={secrets.token_hex(16)}\n"
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
            lock_file.write(owner_contents)
            lock_file.flush()
            os.fsync(lock_file.fileno())
        yield
    finally:
        try:
            if descriptor >= 0:
                os.close(descriptor)
        finally:
            # Do not unlink a replacement lock acquired after an operator or
            # external process removed this sidecar while the original writer
            # was still active. Chronos writers never replace an existing lock.
            try:
                with lock_path.open("r", encoding="ascii") as current_lock:
                    still_ours = current_lock.read() == owner_contents
            except FileNotFoundError:
                still_ours = False
            if still_ours:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass


def fsync_directory(directory: Path) -> None:
    """Persist directory-entry changes where the platform exposes directory fsync.

    Windows does not provide a portable directory-handle fsync through Python's
    standard library, so this operation is skipped there. On POSIX, failures are
    surfaced to the caller; after an atomic replace, the destination may already
    contain the new file even if this durability step fails.
    """
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
