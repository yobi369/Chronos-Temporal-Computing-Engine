from chronos.vector_clock import VectorClock


def test_vector_clock_tracks_happens_before():
    first = VectorClock()
    first.tick('a')
    later = VectorClock({'a': 1})
    later.tick('b')
    assert first.happens_before(later)
    assert not later.happens_before(first)


def test_vector_clock_detects_concurrent_events_and_merges():
    left = VectorClock({'a': 1})
    right = VectorClock({'b': 1})
    assert left.concurrent_with(right)
    left.merge(right, 'a')
    assert left.values == {'a': 2, 'b': 1}
    assert right.happens_before(left)
