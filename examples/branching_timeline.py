"""Compare counterfactual continuations from one checkpoint."""
from chronos.engine import SimulationEngine
from chronos.timeline import Timeline


def apply_delta(event, engine):
    engine.state['value'] += event.payload['delta']


def main():
    engine = SimulationEngine()
    engine.register('delta', apply_delta)
    engine.state['value'] = 10
    engine.schedule(1, 'delta', {'delta': 5})
    engine.run()
    checkpoint = Timeline.capture('baseline', engine)
    optimistic = checkpoint.fork('optimistic', handlers={'delta': apply_delta})
    conservative = checkpoint.fork('conservative', handlers={'delta': apply_delta})
    optimistic.schedule(2, 'delta', {'delta': 20})
    conservative.schedule(2, 'delta', {'delta': -3})
    optimistic.run()
    conservative.run()
    print('baseline:', engine.state['value'])
    print('optimistic:', optimistic.state['value'])
    print('conservative:', conservative.state['value'])


if __name__ == '__main__':
    main()
