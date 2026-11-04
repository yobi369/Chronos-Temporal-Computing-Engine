"""Reproducible experiment metadata and canonical manifests."""
from __future__ import annotations
import json
import os
import platform
import random
from dataclasses import dataclass
from typing import Any
from chronos.event_log import EventLogError, _canonical_json, state_digest

MANIFEST_SCHEMA_VERSION = 1

@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    seed: int
    parameters: dict[str, Any]
    workload: str
    code_revision: str
    python_version: str
    platform_name: str
    schema_version: int = MANIFEST_SCHEMA_VERSION

    @classmethod
    def create(cls, experiment_id: str, *, seed: int, parameters: dict[str, Any],
        workload: str, code_revision: str | None = None) -> ExperimentManifest:
        if not experiment_id or not workload:
            raise ValueError("experiment_id and workload must be non-empty")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        state_digest(parameters)
        return cls(experiment_id, seed, parameters, workload,
            code_revision or os.environ.get("GITHUB_SHA", "working-tree-unknown"),
            platform.python_version(), platform.platform())

    def to_json(self) -> str:
        if self.schema_version != MANIFEST_SCHEMA_VERSION:
            raise EventLogError(f"unsupported manifest schema version: {self.schema_version}")
        return _canonical_json({"schema_version": self.schema_version,
            "experiment_id": self.experiment_id, "seed": self.seed,
            "parameters": self.parameters, "workload": self.workload,
            "code_revision": self.code_revision, "python_version": self.python_version,
            "platform": self.platform_name})

    def rng(self) -> random.Random:
        """Return a deterministic PRNG initialized from this manifest."""
        return random.Random(self.seed)

def manifest_from_json(source: str) -> ExperimentManifest:
    try:
        data = json.loads(source)
    except json.JSONDecodeError as exc:
        raise EventLogError(f"invalid experiment manifest JSON: {exc}") from exc
    expected = {"schema_version", "experiment_id", "seed", "parameters", "workload",
        "code_revision", "python_version", "platform"}
    if not isinstance(data, dict) or set(data) != expected:
        raise EventLogError("manifest has unexpected or missing fields")
    if data["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise EventLogError("unsupported experiment manifest schema version")
    if not isinstance(data["seed"], int) or isinstance(data["seed"], bool):
        raise EventLogError("manifest seed must be an integer")
    for key in ("experiment_id", "workload", "code_revision", "python_version", "platform"):
        if not isinstance(data[key], str) or not data[key]:
            raise EventLogError(f"manifest {key} must be a non-empty string")
    if not isinstance(data["parameters"], dict):
        raise EventLogError("manifest parameters must be an object")
    state_digest(data["parameters"])
    return ExperimentManifest(data["experiment_id"], data["seed"], data["parameters"],
        data["workload"], data["code_revision"], data["python_version"], data["platform"],
        data["schema_version"])
