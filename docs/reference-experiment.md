# Reference experiment: supply resilience under disruption

## Purpose

This workflow demonstrates a narrow, testable Chronos use case: compare
alternative discrete-event futures from one shared checkpoint, then serialize
and replay each branch to verify that the same recorded inputs and handlers
reproduce the same engine snapshot.

The scenario is intentionally small and transparent. It is an engineering
demonstration, not a calibrated logistics model, operational recommendation,
or evidence that Chronos predicts real supply-chain outcomes.

## Run it

From the repository root:

    python -m pip install -e .
    python examples/institutional_resilience_experiment.py

The example uses only the package's public API. It requires no network access,
external service, paid infrastructure, or non-standard runtime dependency.

## Model

The baseline starts with 50 inventory units. At logical time 1, demand for
30 units is fulfilled, leaving 20 units. Chronos captures this state as a
checkpoint. Two isolated branches then receive different shipment quantities
at time 2 and the same demand of 45 units at time 3.

| Scenario | Shipment | New demand | New fulfilment | New shortage | Final inventory |
|---|---:|---:|---:|---:|---:|
| Normal supply | 40 | 45 | 45 | 0 | 15 |
| Disrupted supply | 10 | 45 | 30 | 15 | 0 |

The final state retains baseline totals: the normal branch records 75 total
fulfilled units and zero shortage; the disrupted branch records 60 total
fulfilled units and 15 shortage units.

## Verification performed by the workflow

For each branch, the example:

1. forks from the same captured parent checkpoint;
2. records branch-local driver inputs separately from observed events;
3. captures a versioned timeline-continuation record;
4. serializes and parses the record using Chronos canonical JSON;
5. replays the continuation using the same deterministic handlers; and
6. compares the replayed full engine snapshot with the original branch snapshot.

It prints the resulting state, SHA-256 state digest, serialized record size,
and replay verification result. The automated test asserts both scenario
outcomes, exact replay state equality, distinct state digests, and that
running the branches did not mutate the shared parent checkpoint.

## Interpretation and limits

This workflow illustrates counterfactual branching and reproducible replay
inside one Python process. It does not demonstrate distributed execution,
multi-user collaboration, real-world forecasting accuracy, calibrated demand
models, authenticated audit evidence, or production integration with an ERP,
warehouse, transport, or public-sector system.

A real deployment would need domain-reviewed event definitions, validated
input datasets, explicit model assumptions, independent expected-outcome
checks, access controls, operational monitoring, and deployment-specific
failure testing. The state digest is a reproducibility checksum, not a
cryptographic signature or proof that the modeled assumptions are true.
