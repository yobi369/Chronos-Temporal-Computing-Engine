# ruff: noqa: E701, E702, E501
import math
import pytest
from chronos.hybrid import integrate_adaptive_rk4, integrate_rk4, rk4_step

def decay(t,y): return (-y[0],)
def test_rk4_matches_exponential_and_converges():
    coarse=integrate_rk4(decay,(1.0,),0,1,0.2)
    fine=integrate_rk4(decay,(1.0,),0,1,0.1)
    assert abs(fine.states[-1][0]-math.exp(-1)) < abs(coarse.states[-1][0]-math.exp(-1))
    assert abs(fine.states[-1][0]-math.exp(-1)) < 1e-6
def test_adaptive_rk4_controls_error_and_reports_rejections():
    result=integrate_adaptive_rk4(decay,(1.0,),0,1,initial_step=0.8,atol=1e-10,rtol=1e-8)
    assert abs(result.states[-1][0]-math.exp(-1))<1e-8
    assert result.accepted_steps>0
    assert result.rejected_steps>=0
def test_solver_rejects_invalid_derivative_and_step():
    with pytest.raises(ValueError): rk4_step(lambda t,y:(float("nan"),),0,(1,),0.1)
    with pytest.raises(ValueError): rk4_step(decay,0,(1,),0)
