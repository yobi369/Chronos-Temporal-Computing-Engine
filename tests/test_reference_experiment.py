from examples.institutional_resilience_experiment import (
    build_checkpoint,
    run_scenario,
)


def test_reference_experiment_replays_counterfactual_branches_exactly():
    checkpoint = build_checkpoint()
    checkpoint_before = checkpoint.snapshot

    normal = run_scenario(checkpoint, "normal-supply-test", shipment_units=40)
    disrupted = run_scenario(checkpoint, "disrupted-supply-test", shipment_units=10)

    assert normal["state"] == {
        "inventory": 15,
        "fulfilled": 75,
        "shortage": 0,
    }
    assert disrupted["state"] == {
        "inventory": 0,
        "fulfilled": 60,
        "shortage": 15,
    }
    assert normal["replayed_state"] == normal["state"]
    assert disrupted["replayed_state"] == disrupted["state"]
    assert checkpoint.snapshot == checkpoint_before
    assert normal["state_digest"] != disrupted["state_digest"]
