from hypothesis import given, strategies as st

from chronos.event_log import state_digest


json_scalar = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text()
)
json_value = st.recursive(
    json_scalar,
    lambda children: st.lists(children, max_size=5)
    | st.dictionaries(st.text(min_size=1), children, max_size=5),
    max_leaves=20,
)


@given(st.dictionaries(st.text(min_size=1), json_value, max_size=12))
def test_state_digest_is_independent_of_top_level_insertion_order(state):
    reversed_state = dict(reversed(list(state.items())))
    assert state_digest(state) == state_digest(reversed_state)
