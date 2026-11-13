# Market-readiness programme

**Status:** engineering assessment and release-gate plan; not a declaration that Chronos is production-ready.

Chronos is currently a pre-alpha research software project (package version 0.5.0). Its existing deterministic discrete-event engine, causal clocks and provenance, isolated timeline forks, versioned event logs, deterministic replay, continuation formats, hybrid simulation research, bounded verification, and worker primitives are valuable foundations. They do not by themselves establish production suitability.

This document turns market readiness into explicit, evidence-based release gates. A capability is considered complete only when its implementation, tests, operational behavior, documentation, and limitations agree.

## Product positioning

**Current defensible description:** a Python research engine for deterministic discrete-event simulation, causal event provenance, versioned experiment histories, replay, and branching logical timelines.

Do not market Chronos as a physical time machine, a general-purpose distributed database, a consensus system, a certified numerical solver, an exactly-once execution platform, or a production fault-tolerant cluster.

Initial market discovery should target research groups, simulation developers, and engineering teams that need reproducible discrete-event experiments. Institutional or regulated deployments require a separate threat model, deployment design, operational review, and acceptance testing.

## Release stages

| Stage | Meaning | Exit evidence |
|---|---|---|
| Engineering baseline | Existing functionality is documented and repeatably tested | Clean CI, API inventory, architecture and known-limitations register |
| Alpha candidate | Core workflows are stable for controlled evaluation | Installation matrix, stable public API proposal, security review, migration tests, reproducible examples |
| Beta candidate | External users can evaluate without maintainer intervention | User documentation, sample projects, issue templates, support policy, compatibility policy, performance methodology |
| 1.0 candidate | Compatibility and operational expectations are supportable | Release checklist complete, signed/tagged release process, SBOM/provenance, vulnerability response, tested packaging and upgrade path |
| Production profile | A specific deployment environment has been validated | Deployment-specific threat model, backup/restore and recovery drills, observability, load/failure tests, operator runbook, acceptance sign-off |

Chronos must not skip stages by changing README wording or package classifiers.

## Priority workstreams

### P0 — Correctness and contract clarity

- Preserve event-log schemas v1–v3 and timeline-continuation schemas v1–v2 with immutable golden fixtures.
- Publish machine-readable payload and record schemas, including required fields, bounds, canonicalization rules, and compatibility behavior.
- Specify deterministic handler requirements and the exact boundary between recorded inputs and external effects.
- Deeply freeze or defensively copy event payloads at scheduling and persistence boundaries; prove that caller mutation cannot silently change queued or historical events.
- Add adversarial tests for duplicate identifiers, causal-parent inconsistencies, malformed numeric values, excessive nesting/size, duplicate JSON keys, truncated writes, and corrupted checkpoints.
- Define digest algorithm/version/domain separation and the exact bytes covered by each digest. Digests remain consistency checks, not authenticity proofs.

### P0 — Persistence and recovery contract

- Document the current single-writer local-file persistence guarantee precisely.
- Test concurrent-writer rejection or explicitly enforce the single-writer contract.
- Exercise interrupted writes, stale temporary files, replacement failures, directory fsync behavior where supported, and recovery after process termination.
- Specify filesystem/platform assumptions; do not claim universal power-loss durability.
- Define retention, backup, restore, and event-history export/import procedures before any operational deployment profile is called production-ready.

### P0 — Security and trust boundaries

- Threat-model untrusted event logs, payloads, handlers, worker messages, local files, and filesystem paths.
- Keep replay explicitly separate from sandboxing: replay invokes caller-registered code.
- Validate message size, authentication failure behavior, replay protection, key rotation, and secret handling for worker HMAC.
- Document and test TLS requirements for untrusted networks; HMAC authenticates but does not encrypt.
- Establish dependency vulnerability scanning, supported Python versions, security reporting contact/process, and remediation expectations.
- Do not claim safe multi-tenant isolation until a separate isolation architecture and tests exist.

### P1 — API and package quality

- Inventory exported symbols and mark public, provisional, and internal APIs.
- Define deprecation policy and compatibility promises before 1.0.
- Verify editable install, wheel build, sdist build, clean-environment install, import behavior, and documented quickstart from built artifacts.
- Validate package metadata, license inclusion, package contents, Python version classifiers, and reproducible release artifacts.
- Add API examples that execute in CI and avoid relying on private internals.
- Keep optional research features isolated from the deterministic core and declare optional dependencies only when needed.

### P1 — Test strategy

Maintain separate, named suites for:
- unit and invariant tests;
- integration and persistence tests;
- property-based and differential scheduler tests;
- schema compatibility and migration tests;
- subprocess/fresh-process replay tests;
- cross-platform CI;
- security/adversarial tests;
- numerical reference comparisons for hybrid integration;
- distributed worker fault-injection tests.

Coverage percentage is a useful floor, not a correctness proof. Critical invariants need direct assertions and mutation-resistant tests. Record test counts, platform/Python matrix, and exact commands for every release candidate.

### P1 — Performance and reliability evidence

- Establish stable benchmark scenarios, warmups, repetitions, environment metadata, raw samples, and uncertainty reporting.
- Benchmark scheduling, dispatch, event-log serialization, persistence, replay, snapshots, forks, and worker inbox/outbox separately.
- Include small, medium, and large workloads plus memory measurements.
- Compare only against documented baselines under the same environment.
- Do not publish universal throughput or latency claims from hosted-runner smoke tests.

### P1 — Documentation and adoption

- Provide a five-minute installation and quickstart guide.
- Add end-to-end examples: deterministic run, persist/reload, replay/digest verification, fork/continuation, and payload validation.
- Maintain architecture diagrams, API reference, schema references, migration guides, threat model, operational limitations, and troubleshooting.
- Add CONTRIBUTING, CODE_OF_CONDUCT, issue/PR templates, changelog, release process, and maintainer/support expectations.
- Clearly distinguish implemented capabilities, experimental capabilities, and unimplemented research directions.

### P2 — Institutional and operational profile

Only after the core gates pass:
- define deployment topology and supported storage/network environments;
- add structured logs, metrics, health checks, and operational diagnostics where a service wrapper is justified;
- create backup/restore and disaster-recovery runbooks;
- conduct independent security review and deployment-specific acceptance tests;
- define support, upgrade, incident, and vulnerability response commitments;
- obtain written customer/institutional acceptance before claiming suitability for that environment.

## Initial gaps visible from the current repository

The following are confirmed by current repository documentation/configuration and should be treated as open work, not assumed complete:

1. Package metadata still declares version 0.5.0 and `Development Status :: 2 - Pre-Alpha`.
2. README describes an early-stage research project and explicitly limits event-log persistence to a local single-writer protocol.
3. Event payload dataclasses are not deeply immutable; nested payload values can be mutable.
4. Worker processing is at-least-once; handlers must be idempotent. HMAC does not encrypt transport.
5. Distributed membership, leader election, consensus, partition ownership, and multi-node independent validation are not implemented.
6. Continuations do not capture arbitrary external driver actions or continuous-integrator state.
7. Hybrid root localization detects sign changes only; numerical methods are not certified for stiff systems or global error bounds.
8. Existing hosted CI provides useful cross-platform evidence but does not establish third-party replication, physical power-loss guarantees, or production operational readiness.
9. The current CI workflow checks lint, mypy, tests with a 70% coverage floor, and benchmark smoke/reproduction; package artifact installation and release provenance need explicit gates.

## Acceptance checklist for a 1.0 candidate

A 1.0 candidate is blocked until all applicable items have evidence attached to a release checklist:

- [ ] Public API and compatibility policy approved.
- [ ] Event, payload, event-log, snapshot, and continuation schemas documented and validated.
- [ ] All historical schema golden fixtures remain unchanged and migration paths tested.
- [ ] Payload mutation and aliasing risks resolved or explicitly constrained by the public contract.
- [ ] Persistence concurrency, interruption, corruption, and recovery behavior tested on supported platforms.
- [ ] Security threat model and adversarial test suite reviewed.
- [ ] Worker authentication, replay protection, key management, and TLS guidance tested/documented.
- [ ] Wheel and source distribution built and installed in clean environments on supported Python versions.
- [ ] User-facing examples execute in CI.
- [ ] Cross-platform CI and required benchmark workflows pass on the release commit.
- [ ] Performance claims include raw evidence and environment details.
- [ ] Documentation, changelog, contribution guide, support policy, and known limitations are complete.
- [ ] License and third-party dependency notices are verified.
- [ ] Release artifacts have provenance/checksums and a documented rollback/recovery plan.
- [ ] A named deployment profile has its own operational and acceptance sign-off before production claims.

## Scientific scope boundary

The engine's software semantics and numerical methods must be evaluated as software and mathematics. Relativistic time dilation, quantum temporal effects, closed timelike curves, and physical time travel remain unimplemented research directions. No software milestone, test suite, benchmark, or market-readiness review establishes a physical theory.
