from __future__ import annotations

import pytest

from chronos import (
    CANONICAL_JSON_FORMAT,
    STATE_DIGEST_FORMAT,
    canonical_json_bytes,
    state_digest,
)
from chronos.event_log import EventLogError


def test_canonical_serialization_contract_identifiers_are_stable():
    assert CANONICAL_JSON_FORMAT == "chronos-canonical-json-v1"
    assert STATE_DIGEST_FORMAT == "sha256(chronos-canonical-json-v1)"


def test_empty_state_digest_matches_the_published_vector():
    assert canonical_json_bytes({}) == b"{}"
    assert state_digest({}) == (
        "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    )


def test_unicode_nested_and_float_digest_vector_is_byte_exact():
    state = {
        "z": [True, None, -0.0, 1e-7],
        "é": "naïve",
        "a": {"β": 2},
    }
    expected = '{"a":{"β":2},"z":[true,null,-0.0,1e-07],"é":"naïve"}'.encode()

    assert canonical_json_bytes(state) == expected
    assert state_digest(state) == (
        "e830780abb737ef53eac4b0afdb3bea5e6cf040d94ef816fe5ac39f6c41d6ff4"
    )


def test_canonical_bytes_and_digest_ignore_object_insertion_order():
    left = {"z": 3, "a": {"y": 2, "b": 1}}
    right = {"a": {"b": 1, "y": 2}, "z": 3}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert state_digest(left) == state_digest(right)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_canonical_bytes_reject_non_finite_numbers(value):
    with pytest.raises(EventLogError, match="non-finite"):
        canonical_json_bytes({"value": value})


def test_canonical_bytes_reject_invalid_unicode_surrogates():
    with pytest.raises(EventLogError, match="UTF-8"):
        canonical_json_bytes({"value": "\ud800"})
