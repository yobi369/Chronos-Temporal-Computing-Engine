import pytest

from chronos.causality import CausalGraph
from chronos.events import Event


def test_causal_graph_finds_ancestors_and_descendants():
    events = [
        Event('a', 0, 0, 'root'),
        Event('b', 1, 1, 'child', parent_event_id='a'),
        Event('c', 2, 2, 'grandchild', parent_event_id='b'),
        Event('d', 2, 3, 'other', parent_event_id='a'),
    ]
    graph = CausalGraph(events)
    assert graph.ancestors('c') == {'a', 'b'}
    assert graph.descendants('a') == {'b', 'c', 'd'}
    assert graph.parent_of('b') == 'a'


def test_causal_graph_rejects_forward_parent_and_unknown_node():
    with pytest.raises(ValueError, match='unknown or forward'):
        CausalGraph([Event('child', 1, 1, 'x', parent_event_id='parent')])
    graph = CausalGraph([Event('root', 0, 0, 'x')])
    with pytest.raises(KeyError):
        graph.ancestors('missing')
