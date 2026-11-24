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
