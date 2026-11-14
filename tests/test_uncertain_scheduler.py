# ruff: noqa: E501, E701, E702
import pytest
from chronos.engine import SimulationEngine
from chronos.uncertainty import TimeInterval,propagate_order_probabilities

def test_uncertain_event_uses_explicit_conservative_upper_bound():
    engine=SimulationEngine(); seen=[]
    engine.register("capture",lambda event,sim:seen.append(event))
    event=engine.schedule_uncertain(TimeInterval(1.2,3.1),"capture",{"v":7})
    assert event.time==4
    assert event.payload["uncertain_time"]=={"lower":1.2,"upper":3.1,"policy":"upper_bound"}
    engine.run()
    assert seen[0].time==4

def test_probability_propagation_is_reproducible_and_normalized():
    intervals=(TimeInterval(0,2),TimeInterval(1,3))
    a=propagate_order_probabilities(intervals,samples=5000,seed=42)
    b=propagate_order_probabilities(intervals,samples=5000,seed=42)
    assert a==b
    assert sum(x.probability for x in a.outcomes)==pytest.approx(1)
    assert len(a.outcomes)==2
