# Release process

This document defines how Chronos moves from research development to a public release. A release is an evidence-backed engineering decision, not a change of package classifier or README wording.

## Release stages

1. **Research development** — features and semantics may evolve; public APIs can remain provisional.
2. **Alpha evaluation** — core workflows, installation, compatibility, known limitations, and security boundaries are documented and repeatably tested.
3. **Beta evaluation** — external developers can install and reproduce reference experiments without maintainer intervention; support and compatibility expectations are published.
4. **Release candidate** — the proposed release commit has passed the full required CI matrix, artifact verification, clean-environment installation, compatibility tests, and release checklist review.
5. **Stable release** — the release candidate is accepted, versioned, tagged, and published with checksums and provenance.
6. **Deployment profile** — production suitability is assessed for a specific customer environment, topology, data classification, and operational model. A stable library release alone does not establish this.

Stages may not be skipped by changing metadata alone.

## Release candidate acceptance

Before proposing a release candidate, attach evidence for:

- [ ] A reviewed public API inventory and compatibility/deprecation policy.
- [ ] Passing lint, type checks, full test suite, coverage threshold, distribution verification, and benchmark smoke/reproduction on the required CI matrix.
- [ ] Built wheel and source distribution installed in clean environments.
- [ ] Supported Python versions and operating systems explicitly stated and tested.
- [ ] Event-log v1/v2/v3, snapshot v1/v2, and continuation v1/v2 compatibility fixtures preserved and migration behavior tested.
- [ ] Persistence interruption, corruption, concurrency, and recovery boundaries tested and documented.
- [ ] Security threat model, dependency review, vulnerability disclosure route, and replay/worker trust boundaries documented.
- [ ] Reproducible end-to-end examples covering simulation, persistence, replay, verification, and branching.
- [ ] Performance evidence with raw results and environment details; no universal claims based on hosted-runner smoke tests.
- [ ] Changelog, installation guide, API reference, known limitations, contribution guidance, and support expectations complete.
- [ ] Independent clean-environment reproduction and appropriate external review recorded.
- [ ] License and third-party notices verified.
- [ ] Release artifacts, checksums, provenance, and rollback/recovery notes prepared.

Any unresolved critical correctness or security issue blocks the release candidate.

## Versioning and compatibility

- Keep the package version and release tag synchronized.
- Use a new version for every published release; do not overwrite or retag an existing release.
- Preserve published wire-format schemas and canonical golden fixtures.
- Introduce a separately versioned format for incompatible serialization changes.
- State whether APIs are stable, provisional, or internal.
- Document migration and deprecation behavior before removing or changing supported interfaces.

The initial stable version number is not preselected here. It must follow the compatibility policy and the evidence available at release time.

## Release execution

After explicit maintainer approval of the exact release candidate:

1. Freeze the candidate commit and verify its full commit SHA.
2. Confirm the required CI runs refer to that exact SHA and completed successfully.
3. Build wheel and source distribution from the candidate tag/commit.
4. Inspect package contents, metadata, license files, dependency declarations, and checksums.
5. Generate software bill of materials and build provenance where supported.
6. Publish the changelog and installation/migration notes.
7. Create a versioned Git tag and GitHub release only after acceptance.
8. Verify the published artifacts by downloading and installing them in a clean environment.
9. Publish a release announcement that describes implemented capabilities and limitations accurately.
10. Track early-user reports and security issues through the documented support channels.

Do not merge a development branch, create a tag, publish a package, or announce production readiness merely because an intermediate CI run passes.

## Production deployment claims

A production claim must identify the exact deployment profile and include operational evidence for storage, backup/restore, recovery, observability, load, failure handling, security, data retention, and customer acceptance. Chronos does not provide consensus, exactly-once side effects, arbitrary replay sandboxing, or universal filesystem durability.
