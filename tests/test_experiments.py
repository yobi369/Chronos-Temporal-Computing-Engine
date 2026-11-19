import json
import pytest
from chronos.event_log import EventLogError
from chronos.experiments import ExperimentManifest, manifest_from_json

def test_manifest_round_trip_and_seed_reproducibility():
    manifest = ExperimentManifest.create("repro-1", seed=12345,
        parameters={"steps": 100, "rate": 0.25},
        workload="synthetic workload", code_revision="abc123")
    restored = manifest_from_json(manifest.to_json())
    assert restored == manifest
    assert [manifest.rng().random() for _ in range(3)] == [
        manifest.rng().random() for _ in range(3)]

def test_manifest_rejects_unknown_fields():
    manifest = ExperimentManifest.create("repro-2", seed=7, parameters={}, workload="empty")
    document = json.loads(manifest.to_json())
    document["untracked"] = True
    with pytest.raises(EventLogError, match="unexpected"):
        manifest_from_json(json.dumps(document))
