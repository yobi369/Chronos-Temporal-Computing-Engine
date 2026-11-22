"""Tests for cooperative persistence filesystem helpers."""
from __future__ import annotations

import os

from chronos._file_lock import fsync_directory


def _unexpected_open(*args, **kwargs):
    raise AssertionError("directory handles are not opened on Windows")


def test_fsync_directory_uses_supported_platform_behavior(tmp_path, monkeypatch):
    if os.name == "nt":
        monkeypatch.setattr(os, "open", _unexpected_open)
        fsync_directory(tmp_path)
        return

    fsync_directory(tmp_path)
