# Portable experiment reports

Chronos can package persisted event logs and timeline continuations into a portable report directory. The report contains validated copies of the source artifacts, metadata summaries, and SHA-256 file digests.

## Create a report

After generating artifacts with an experiment, create a report bundle:

    chronos create-report \
      --output-dir review-bundle \
      --event-log chronos-artifacts/run-a.event-log.json \
      --continuation chronos-artifacts/normal-supply.continuation.json \
      --continuation chronos-artifacts/disrupted-supply.continuation.json

To sign the manifest using an externally managed Ed25519 private key, add `--signing-key /secure/path/reviewer-ed25519-private.pem`. Encrypted PEM keys prompt for their passphrase. The private key is never included in the bundle. Install support with `pip install 'chronos-temporal-computing-engine[signing]'`. A detached `signature.json` signs the exact bytes of `report.json`.

Each input is validated before and after copying. The output directory must not already exist; Chronos will not overwrite an existing report. The bundle contains:

    review-bundle/
      report.json
      artifacts/
        artifact-001-event_log.json
        artifact-002-timeline_continuation.json
        artifact-003-timeline_continuation.json

The report records the Chronos version, artifact types, original filenames, schema-aware metadata, and SHA-256 digests. State and event payload values are not copied into the metadata summary; the original validated artifacts are included unchanged.

## Verify a received report

After transferring the entire directory, run:

    chronos verify-report review-bundle
    chronos verify-report review-bundle --json

For a local trust decision, supply the expected PEM public key:

    chronos verify-report review-bundle --trusted-public-key /secure/path/reviewer-ed25519-public.pem

Verification checks that each bundled file remains within the supported size limit, matches its recorded SHA-256 digest, parses under the supported Chronos schema, and reproduces the report's metadata summary. A successful result confirms the integrity and structural validity of the included files relative to the report.

## Verification boundary

This is a portable integrity and metadata check, **not a replay of the experiment**. The command does not execute user handlers, reconstruct hidden dependencies, independently validate the scientific model, or establish that the reported scenario is realistic. Replay remains a separate workflow requiring the original deterministic handlers and controlled inputs.

SHA-256 digests alone do not prove origin. Signed reports are verified with Ed25519 over the exact manifest bytes. A valid signature without a matching `--trusted-public-key` is **valid but untrusted**. A matching key is a local policy decision, not proof of legal identity, authorization, revocation status, or trusted time. Version 1 has no certificate discovery, revocation, expiry, or timestamp service. Keep private keys outside bundles and manage key custody independently. See [signed report format](signed-report-format.md).

The report format is versioned independently from event-log and continuation schemas. The current report schema is version 1.
