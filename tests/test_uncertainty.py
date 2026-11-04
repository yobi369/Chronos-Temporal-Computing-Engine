# ruff: noqa: E701, E702, E501
import pytest
from chronos.uncertainty import TimeInterval, possible_orders

def test_interval_precedence_and_overlap():
    a=TimeInterval(1,2); b=TimeInterval(3,4); c=TimeInterval(2,3)
    assert a.definitely_before(b)
    assert a.overlaps(c)
    assert a.intersection(c)==TimeInterval(2,2)
    assert a.hull(c)==TimeInterval(1,3)
def test_possible_orders_respects_only_definite_precedence():
    orders=possible_orders((TimeInterval(0,1),TimeInterval(3,4),TimeInterval(0,4)))
    assert orders
    assert all(order.index(0)<order.index(1) for order in orders)
def test_interval_validation_and_enumeration_bound():
    with pytest.raises(ValueError): TimeInterval(2,1)
    with pytest.raises(ValueError): possible_orders(tuple(TimeInterval(i,i) for i in range(9)))
