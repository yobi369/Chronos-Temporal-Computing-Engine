# Reference experiment: supply resilience under disruption

## Purpose

This workflow demonstrates a narrow, testable Chronos use case: compare
alternative discrete-event futures from one shared checkpoint, export each
branch as a portable continuation artifact, then verify those artifacts in a
separate Python process.

The scenario is intentionally small and transparent. It is an engineering
demonstration, not a calibrated logistics model, operational recommendation,
or evidence that Chronos predicts real supply-chain outcomes.

## Run it

From the repository root:

    python -m pip install -e .
    python examples/institutional_resilience_experiment.py --output-dir chronos-artifacts

The command creates two portable JSON continuation files:

- `chronos-artifacts/normal-supply.continuation.json`
- `chronos-artifacts/disrupted-supply.continuation.json`

Verify the saved files in a separate process:

    python examples/institutional_resilience_experiment.py --verify-artifacts chronos-artifacts

The verifier loads each file from disk, validates its continuation record,
reconstructs the branch using the declared deterministic handlers, checks the
expected scenario state, and prints an explicit PASS result and state digest.

## Package a reviewer report

Once the continuation files have been generated, package both into a portable
report directory:

    chronos create-report \
      --output-dir investor-review \
      --continuation chronos-artifacts/normal-supply.continuation.json \
      --continuation chronos-artifacts/disrupted-supply.continuation.json

Verify the report from a separate process:

    chronos verify-report investor-review
    chronos verify-report investor-review --json

Share the complete `investor-review/` directory with the reviewer. It contains
the original validated continuation artifacts, a metadata summary, and
SHA-256 digests. The verifier checks artifact integrity and schema validity;
it does not replay the simulation. To independently reproduce the scenario
outcomes, the reviewer should also run the example's fresh-process replay
command above. See [portable experiment reports](experiment-reports.md) for
the report format and its verification boundaries.

The workflow is local and requires no network access, external service, or
paid infrastructure.

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
4. serializes and writes the record using Chronos canonical JSON;
5. reads the persisted file back through Chronos validation;
6. replays the continuation and compares the full engine snapshot; and
7. supports a second, independent process that reloads the exported files,
   replays both branches, and checks their expected final states.

The automated test launches the example to export artifacts, then starts a
second Python interpreter to verify them. This checks the documented
cross-process workflow rather than merely reusing in-memory Python objects.

## Interpretation and limits

This workflow illustrates counterfactual branching and reproducible replay
inside one Python runtime per process. It does not demonstrate distributed
execution, multi-user collaboration, real-world forecasting accuracy,
calibrated demand models, authenticated audit evidence, or production
integration with an ERP, warehouse, transport, or public-sector system.

A real deployment would need domain-reviewed event definitions, validated
input datasets, explicit model assumptions, independent expected-outcome
checks, access controls, operational monitoring, and deployment-specific
failure testing. The state digest is a reproducibility checksum, not a
cryptographic signature or proof that the modeled assumptions are true.
