"""Tests for cooperative persistence filesystem helpers."""
from __future__ import annotations

import os

import pytest

from chronos._file_lock import exclusive_file_lock, fsync_directory


def _unexpected_open(*args, **kwargs):
    raise AssertionError("directory handles are not opened on Windows")


def test_fsync_directory_uses_supported_platform_behavior(tmp_path, monkeypatch):
    if os.name == "nt":
        monkeypatch.setattr(os, "open", _unexpected_open)
        fsync_directory(tmp_path)
        return

    fsync_directory(tmp_path)


def test_lock_release_preserves_a_replacement_sidecar(tmp_path):
    destination = tmp_path / "experiment.json"
    lock_path = tmp_path / ".experiment.json.lock"
    replacement = b"replacement lock with non-UTF8 metadata: \xff\xfe"

    with exclusive_file_lock(
        destination,
        error_factory=lambda message: RuntimeError(message),
    ):
        lock_path.unlink()
        lock_path.write_bytes(replacement)

    assert lock_path.read_bytes() == replacement
    with pytest.raises(RuntimeError, match="writer lock already exists"):
        with exclusive_file_lock(
            destination,
            error_factory=lambda message: RuntimeError(message),
        ):
            pass


def test_lock_setup_failure_removes_a_partially_written_sidecar(tmp_path, monkeypatch):
    destination = tmp_path / "experiment.json"
    lock_path = tmp_path / ".experiment.json.lock"
    real_fdopen = os.fdopen

    class PartialWriter:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.wrapped.close()
            return False

        def write(self, contents):
            self.wrapped.write(contents[:4])
            self.wrapped.flush()
            raise OSError("simulated partial lock write")

        def flush(self):
            self.wrapped.flush()

        def fileno(self):
            return self.wrapped.fileno()

    monkeypatch.setattr(
        os,
        "fdopen",
        lambda descriptor, mode: PartialWriter(real_fdopen(descriptor, mode)),
    )

    with pytest.raises(OSError, match="simulated partial lock write"):
        with exclusive_file_lock(
            destination,
            error_factory=lambda message: RuntimeError(message),
        ):
            pytest.fail("lock initialization must fail before entering the context")

    assert not lock_path.exists()


def test_fdopen_failure_removes_the_empty_sidecar(tmp_path, monkeypatch):
    destination = tmp_path / "experiment.json"
    lock_path = tmp_path / ".experiment.json.lock"

    def fail_fdopen(descriptor, mode):
        raise OSError("simulated fdopen failure")

    monkeypatch.setattr(os, "fdopen", fail_fdopen)

    with pytest.raises(OSError, match="simulated fdopen failure"):
        with exclusive_file_lock(
            destination,
            error_factory=lambda message: RuntimeError(message),
        ):
            pytest.fail("lock initialization must fail before entering the context")

    assert not lock_path.exists()


def test_lock_release_does_not_follow_a_replacement_symlink(tmp_path):
    destination = tmp_path / "experiment.json"
    lock_path = tmp_path / ".experiment.json.lock"
    target = tmp_path / "unrelated-target"
    target.write_bytes(b"keep this file")

    with exclusive_file_lock(
        destination,
        error_factory=lambda message: RuntimeError(message),
    ):
        lock_path.unlink()
        try:
            lock_path.symlink_to(target)
        except (NotImplementedError, OSError):
            pytest.skip("symlink creation is unavailable on this platform")

    assert lock_path.is_symlink()
    assert target.read_bytes() == b"keep this file"
