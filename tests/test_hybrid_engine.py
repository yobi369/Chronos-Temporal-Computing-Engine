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
    assert engine.current_time==3
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
    assert engine.current_time==2


def test_rk4_fourth_order_convergence_on_exponential():
    from chronos.hybrid import integrate_rk4
    def rhs(t, y):
        return (y[0],)
    coarse=integrate_rk4(rhs,(1.0,),0.0,1.0,0.2).states[-1][0]
    fine=integrate_rk4(rhs,(1.0,),0.0,1.0,0.1).states[-1][0]
    exact=2.718281828459045
    coarse_error=abs(coarse-exact)
    fine_error=abs(fine-exact)
    assert coarse_error/fine_error>12.0
    assert fine_error<coarse_error

def test_adaptive_rk4_meets_requested_local_tolerance():
    from chronos.hybrid import integrate_adaptive_rk4
    result=integrate_adaptive_rk4(lambda t,y:(y[0],),(1.0,),0.0,1.0,
        initial_step=0.5,atol=1e-11,rtol=1e-10)
    assert result.states[-1][0]==pytest.approx(2.718281828459045,abs=2e-9)
    assert result.accepted_steps>0
    assert result.rejected_steps>0

def test_adaptive_rk4_rejects_non_finite_controls_and_state():
    from chronos.hybrid import integrate_adaptive_rk4
    with pytest.raises(ValueError):
        integrate_adaptive_rk4(lambda t,y:(1.0,),(float("nan"),),0.0,1.0,initial_step=0.1)
    with pytest.raises(ValueError):
        integrate_adaptive_rk4(lambda t,y:(1.0,),(0.0,),0.0,float("inf"),initial_step=0.1)


def test_resuming_from_root_does_not_emit_same_root_again():
    engine = SimulationEngine()
    engine.register("threshold", lambda event, sim: None)
    def root(t, y):
        return y[0] - 1.0
    first = engine.integrate_continuous(
        lambda t, y: (1.0,), (0.0,), start=0.0, stop=2.0, step=0.5,
        root_events={"hit": ("threshold", root, {})},
    )
    assert first.root_event is not None
    assert first.root_event.time == pytest.approx(1.0)
    resumed = engine.integrate_continuous(
        lambda t, y: (1.0,), first.root_event.state,
        start=first.root_event.time, stop=2.0, step=0.25,
        root_events={"hit": ("threshold", root, {})},
    )
    assert resumed.root_event is None
    assert resumed.reached_boundary == 2.0
