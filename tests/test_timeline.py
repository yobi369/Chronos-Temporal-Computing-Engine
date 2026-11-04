from chronos.engine import SimulationEngine
from chronos.timeline import Timeline


def test_forks_are_isolated_from_parent_and_each_other():
    def add(event, engine):
        engine.state['total'] += event.payload['amount']
    engine = SimulationEngine()
    engine.register('add', add)
    engine.state['total'] = 10
    engine.schedule(1, 'add', {'amount': 2})
    engine.run()
    checkpoint = Timeline.capture('checkpoint', engine)
    left = checkpoint.fork('left', handlers={'add': lambda e, s: s.state.update(total=99)})
    right = checkpoint.fork('right', handlers={'add': lambda e, s: s.state.update(total=7)})
    left.schedule(2, 'add', {'amount': 1})
    right.schedule(2, 'add', {'amount': 1})
    left.run()
    right.run()
    assert engine.state['total'] == 12
    assert left.state['total'] == 99
    assert right.state['total'] == 7
