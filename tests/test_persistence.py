"""Tests for explicit recovery of abandoned persistence temporary files."""
from __future__ import annotations

import os
import time

import pytest

import chronos.persistence as persistence_module
from chronos import EventLogError, cleanup_stale_temporary_files
from chronos._file_lock import exclusive_file_lock


def _make_old_file(path, *, age_seconds=7200):
    path.write_text("abandoned temporary contents", encoding="utf-8")
    old_time = time.time() - age_seconds
    os.utime(path, (old_time, old_time))


def test_cleanup_removes_only_old_matching_regular_files(tmp_path):
    destination = tmp_path / "experiment.json"
    old_one = tmp_path / ".experiment.json.orphan-one.tmp"
    old_two = tmp_path / ".experiment.json.orphan-two.tmp"
    fresh = tmp_path / ".experiment.json.active.tmp"
    unrelated = tmp_path / ".other.json.orphan.tmp"
    directory = tmp_path / ".experiment.json.directory.tmp"

    _make_old_file(old_one)
    _make_old_file(old_two)
    fresh.write_text("possibly active", encoding="utf-8")
    _make_old_file(unrelated)
    directory.mkdir()

    removed = cleanup_stale_temporary_files(
        destination, minimum_age_seconds=3600
    )

    assert removed == (old_one.name, old_two.name)
    assert not old_one.exists()
    assert not old_two.exists()
    assert fresh.exists()
    assert unrelated.exists()
    assert directory.is_dir()
    assert not (tmp_path / ".experiment.json.lock").exists()


def test_cleanup_ignores_symlinks(tmp_path):
    destination = tmp_path / "experiment.json"
    target = tmp_path / "unrelated-target"
    link = tmp_path / ".experiment.json.link.tmp"
    target.write_text("keep", encoding="utf-8")
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("symlink creation is unavailable on this platform")

    removed = cleanup_stale_temporary_files(
        destination, minimum_age_seconds=1
    )

    assert removed == ()
    assert link.is_symlink()
    assert target.read_text(encoding="utf-8") == "keep"


def test_cleanup_fails_closed_while_a_chronos_writer_lock_exists(tmp_path):
    destination = tmp_path / "experiment.json"
    abandoned = tmp_path / ".experiment.json.abandoned.tmp"
    _make_old_file(abandoned)

    with exclusive_file_lock(destination, error_factory=EventLogError):
        with pytest.raises(EventLogError, match="writer lock"):
            cleanup_stale_temporary_files(
                destination, minimum_age_seconds=3600
            )
        assert abandoned.exists()

    assert abandoned.exists()


@pytest.mark.parametrize(
    "age",
    [True, False, 0, -1, float("nan"), float("inf"), "3600"],
)
def test_cleanup_rejects_invalid_age_thresholds(tmp_path, age):
    with pytest.raises(ValueError, match="positive finite"):
        cleanup_stale_temporary_files(
            tmp_path / "experiment.json", minimum_age_seconds=age
        )


def test_cleanup_returns_empty_when_destination_directory_is_missing(tmp_path):
    assert cleanup_stale_temporary_files(
        tmp_path / "missing" / "experiment.json"
    ) == ()


def test_cleanup_fsyncs_parent_directory_after_removal(tmp_path, monkeypatch):
    destination = tmp_path / "experiment.json"
    abandoned = tmp_path / ".experiment.json.abandoned.tmp"
    _make_old_file(abandoned)
    calls = []

    def tracked_sync(directory):
        calls.append(directory)

    monkeypatch.setattr(persistence_module, "fsync_directory", tracked_sync)

    removed = cleanup_stale_temporary_files(
        destination, minimum_age_seconds=3600
    )

    assert removed == (abandoned.name,)
    assert calls == [tmp_path]


def test_cleanup_reports_directory_sync_failure_after_deletion(tmp_path, monkeypatch):
    destination = tmp_path / "experiment.json"
    abandoned = tmp_path / ".experiment.json.abandoned.tmp"
    _make_old_file(abandoned)

    def fail_sync(directory):
        raise OSError("simulated directory fsync failure")

    monkeypatch.setattr(persistence_module, "fsync_directory", fail_sync)

    with pytest.raises(OSError, match="simulated directory fsync failure"):
        cleanup_stale_temporary_files(
            destination, minimum_age_seconds=3600
        )

    assert not abandoned.exists()
    assert not (tmp_path / ".experiment.json.lock").exists()
