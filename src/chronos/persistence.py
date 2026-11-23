"""Explicit recovery helpers for local Chronos persistence artifacts."""
from __future__ import annotations

import math
import os
import stat
import time
from pathlib import Path

from chronos._file_lock import exclusive_file_lock, fsync_directory
from chronos.event_log import EventLogError

DEFAULT_MINIMUM_TEMPORARY_FILE_AGE_SECONDS = 24 * 60 * 60


def cleanup_stale_temporary_files(
    path: str | Path,
    *,
    minimum_age_seconds: float = DEFAULT_MINIMUM_TEMPORARY_FILE_AGE_SECONDS,
) -> tuple[str, ...]:
    """Explicitly remove old Chronos temporary files for one destination.

    This operation is never called automatically by readers or writers. It
    acquires the destination's normal sidecar lock, removes only matching
    regular files older than the requested threshold, and fsyncs the parent
    directory after removals where supported. Symlinks and directories are
    ignored. A pre-existing lock is treated as an active or unrecovered writer
    and causes the operation to fail closed.
    """
    if (
        isinstance(minimum_age_seconds, bool)
        or not isinstance(minimum_age_seconds, (int, float))
    ):
        raise ValueError("minimum_age_seconds must be a positive finite number")
    try:
        age_seconds = float(minimum_age_seconds)
    except OverflowError as exc:
        raise ValueError("minimum_age_seconds must be a positive finite number") from exc
    if not math.isfinite(age_seconds) or age_seconds <= 0:
        raise ValueError("minimum_age_seconds must be a positive finite number")

    destination = Path(path)
    if not destination.name or (destination.exists() and destination.is_dir()):
        raise ValueError("path must identify a destination file")
    directory = destination.parent
    if not directory.is_dir():
        return ()

    prefix = f".{destination.name}."
    cutoff = time.time() - age_seconds
    removed: list[str] = []

    with exclusive_file_lock(destination, error_factory=EventLogError):
        with os.scandir(directory) as entries:
            candidate_names = sorted(
                entry.name
                for entry in entries
                if entry.name.startswith(prefix) and entry.name.endswith(".tmp")
            )

        for name in candidate_names:
            candidate = directory / name
            try:
                observed = candidate.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(observed.st_mode) or observed.st_mtime > cutoff:
                continue

            # Recheck identity and age immediately before unlinking. The
            # cooperative lock excludes Chronos writers; this second lstat
            # avoids deleting an entry that was replaced during enumeration.
            try:
                current = candidate.lstat()
            except FileNotFoundError:
                continue
            if (
                not stat.S_ISREG(current.st_mode)
                or current.st_dev != observed.st_dev
                or current.st_ino != observed.st_ino
                or current.st_mtime_ns != observed.st_mtime_ns
            ):
                continue

            try:
                candidate.unlink()
            except FileNotFoundError:
                continue
            removed.append(name)

        if removed:
            fsync_directory(directory)

    return tuple(removed)
