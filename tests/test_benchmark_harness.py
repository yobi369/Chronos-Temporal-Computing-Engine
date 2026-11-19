"""Tests for the paired benchmark's statistical helper."""

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "run_benchmarks.py"
SPEC = importlib.util.spec_from_file_location("chronos_benchmark_harness", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def test_bootstrap_median_interval_is_reproducible():
    values = [1.0, 2.0, 3.0, 4.0, 100.0]
    first = benchmark.bootstrap_median_ci(values, seed=17, draws=500)
    second = benchmark.bootstrap_median_ci(values, seed=17, draws=500)

    assert first == second
    assert first[0] <= 3.0 <= first[1]


def test_bootstrap_median_interval_rejects_empty_observations():
    with pytest.raises(ValueError, match="at least one observation"):
        benchmark.bootstrap_median_ci([], seed=1)


def test_bootstrap_median_interval_rejects_non_positive_draws():
    with pytest.raises(ValueError, match="draws must be positive"):
        benchmark.bootstrap_median_ci([1.0, 2.0], seed=1, draws=0)
