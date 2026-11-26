"""Cooperative exclusive locks for local artifact writers."""
from __future__ import annotations

import os
import secrets
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path


def _same_regular_file(observed: os.stat_result, expected: os.stat_result) -> bool:
    return (
        stat.S_ISREG(observed.st_mode)
        and observed.st_dev == expected.st_dev
        and observed.st_ino == expected.st_ino
    )


def _lock_path_matches(
    lock_path: Path,
    *,
    identity: os.stat_result,
    owner_contents: bytes,
    allow_partial: bool,
) -> bool:
    """Check a lock sidecar without following symlinks or blocking on special files."""
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(lock_path, flags)
    except OSError:
        return False

    try:
        opened = os.fstat(descriptor)
        if not _same_regular_file(opened, identity):
            return False
        actual = os.read(descriptor, len(owner_contents) + 1)
    except OSError:
        return False
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass

    try:
        current_path = lock_path.lstat()
    except OSError:
        return False
    if not _same_regular_file(current_path, identity):
        return False

    if allow_partial:
        return len(actual) <= len(owner_contents) and owner_contents.startswith(actual)
    return actual == owner_contents


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
    The owner marker and file identity prevent a normal release from deleting a
    different lock file that replaced this acquisition's sidecar.
    """
    lock_path = destination.with_name(f".{destination.name}.lock")
    owner_contents = f"pid={os.getpid()}\nowner={secrets.token_hex(16)}\n".encode(
        "ascii"
    )
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
        identity = os.fstat(descriptor)
    except OSError:
        # Without the descriptor identity we cannot prove that the path still
        # names the file created by this acquisition. Close the descriptor but
        # leave the sidecar in place for explicit operator inspection.
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise

    initialized = False
    try:
        lock_file = os.fdopen(descriptor, "wb")
        descriptor = -1
        with lock_file:
            lock_file.write(owner_contents)
            lock_file.flush()
            os.fsync(lock_file.fileno())
        initialized = True
        yield
    finally:
        try:
            if descriptor >= 0:
                os.close(descriptor)
        finally:
            # If lock initialization failed part-way through, only a prefix of
            # our marker may have reached disk. In that case the inode identity
            # is sufficient to clean up the file we just created. After a
            # successful initialization, require the complete owner marker.
            still_ours = _lock_path_matches(
                lock_path,
                identity=identity,
                owner_contents=owner_contents,
                allow_partial=not initialized,
            )
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
