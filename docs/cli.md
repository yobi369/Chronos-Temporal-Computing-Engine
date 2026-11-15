# Chronos command-line interface

The Chronos CLI supports read-only artifact inspection, portable report creation and verification, and offline HTML rendering. Commands operate on local files and do not contact a hosted Chronos service.

## Installation

Install the package:

    python -m pip install chronos-temporal-computing-engine

For repository development:

    python -m pip install -e '.[dev]'

The package exposes both the chronos executable and Python module entry point. Optional Ed25519 report signing is installed separately:

    python -m pip install 'chronos-temporal-computing-engine[signing]'

## Inspect persisted artifacts

Show the installed version:

    chronos --version
    python -m chronos --version

Inspect an event log:

    chronos inspect-event-log path/to/event-log.json
    chronos inspect-event-log path/to/event-log.json --json

Inspect a timeline continuation:

    chronos inspect-continuation path/to/continuation.json
    chronos inspect-continuation path/to/continuation.json --json

Inspection validates the artifact and reports schema/version information, timeline identifiers, event counts and types, declared payload contracts, state field names, and recorded digests. It deliberately does not print event payload values or simulation state values. Inspection does not execute handlers or replay a simulation.

## Create a portable report

Package one or more validated event logs and timeline continuations:

    chronos create-report --output-dir review-bundle --event-log path/to/event-log.json
    chronos create-report --output-dir review-bundle --continuation path/to/continuation.json

Add --signing-key to create a detached Ed25519 signature over the exact bytes of report.json:

    chronos create-report --output-dir signed-review --event-log path/to/event-log.json --signing-key /secure/path/reviewer-private.pem

Signing requires the optional cryptography dependency. Chronos accepts an externally managed PEM Ed25519 private key; encrypted keys prompt for a passphrase. Private keys are not generated, stored, printed, or included in the report. The report destination must not already exist.

## Verify a report

Verify artifact hashes, schemas, metadata, and any detached signature:

    chronos verify-report review-bundle
    chronos verify-report review-bundle --json

For a local trust decision, provide the expected PEM Ed25519 public key:

    chronos verify-report signed-review --trusted-public-key /secure/path/reviewer-public.pem

The JSON result keeps integrity_verified, signature_valid, and trust_status separate. A signed report with a mathematically valid signature but no matching trusted key is reported as valid but untrusted. The command can exit successfully in that case; a workflow that requires a trusted signer must check trust_status or provide the expected public key. A wrong trusted key does not turn a valid signature into a trusted one.

An unsigned report remains verifiable for structural and SHA-256 integrity checks and reports trust_status as unsigned. Invalid signatures, manifest changes, artifact tampering, unsupported formats, and malformed artifacts fail verification.

## Render an offline reviewer document

Render a verified report as a self-contained HTML file:

    chronos render-report review-bundle
    chronos render-report signed-review --trusted-public-key /secure/path/reviewer-public.pem
    chronos render-report review-bundle --output /path/to/reviewer-summary.html

The default output is review-bundle/index.html. Rendering first verifies the report and refuses to write HTML when verification fails. Report-derived text is HTML-escaped. The page uses embedded CSS, contains no JavaScript, and does not load remote scripts, fonts, images, or services. It is a local presentation artifact, not a hosted portal.

## Exit behavior and security boundary

Successful inspection, report creation, verification, and rendering exit with status 0. Invalid, unsupported, unreadable, oversized, or tampered inputs produce a diagnostic on standard error and exit with status 2. A valid-but-untrusted signature is not an error; inspect trust_status.

SHA-256 digests detect changes relative to the report manifest but do not authenticate an author. Ed25519 verifies possession of the private key corresponding to the embedded public key. A signer is considered trusted only when the key exactly matches a public key supplied by the reviewer. This does not establish legal identity, organizational authorization, revocation status, trusted time, or key custody.

Report verification is not simulation replay, scientific validation, a sandbox for untrusted handlers, or proof that model assumptions are realistic. Replay requires deterministic handlers and controlled recorded inputs. See the portable report and security/provenance documentation for the full boundaries.
