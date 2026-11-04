import pytest
from chronos.clock import LogicalClock


def test_lamport_clock_tick_and_observe():
    clock = LogicalClock()
    assert clock.tick() == 1
    assert clock.observe(8) == 9
    assert clock.tick() == 10


def test_negative_clock_values_are_rejected():
    with pytest.raises(ValueError):
        LogicalClock(-1)
    with pytest.raises(ValueError):
        LogicalClock().observe(-1)
