# ruff: noqa: E501, E701, E702
import pytest
from chronos.engine import SimulationEngine

def test_engine_localizes_root_and_schedules_boundary_event():
    engine=SimulationEngine()
    seen=[]
    engine.register("threshold",lambda event,sim: seen.append(event.payload))
    result=engine.integrate_continuous(lambda t,y:(1.0,), (0.0,), start=0,stop=4,step=0.8,
        root_events={"threshold":("threshold",lambda t,y:y[0]-2.25,{"kind":"crossing"})})
    assert result.root_event is not None
    assert abs(result.root_event.time-2.25)<1e-8
    assert engine.pending_events[0].time==3
    engine.run()
    assert seen[0]["root_time"]==pytest.approx(2.25)
    assert seen[0]["root_state"]==pytest.approx([2.25])

def test_hybrid_integration_stops_at_next_discrete_event_boundary():
    engine=SimulationEngine()
    engine.register("noop",lambda event,sim:None)
    engine.schedule(2,"noop")
    result=engine.integrate_continuous(lambda t,y:(1.0,),(0.0,),start=0,stop=5,step=0.5)
    assert result.root_event is None
    assert result.reached_boundary==2
    assert result.integration.times[-1]==2
