# Chronos commercial product brief

**Document status:** product strategy baseline for customer discovery. This is not a claim of production readiness, a final price list, or a commitment to an unbuilt hosted service.

## 1. Product thesis

Chronos should help engineering and research teams make event-driven experiments reproducible and explainable.

**Working product description**

> Chronos is a Python-native environment for deterministic event simulation, causal event inspection, controlled timeline branching, and replay verification.

The customer outcome is not "temporal computing" as an abstract concept. It is the ability to answer, with a portable experiment record:

- What initial state and declared inputs produced this result?
- Which events and declared causal relationships led to the outcome?
- Can the experiment be replayed in a clean process and its recorded history and final state checked?
- What changes when one controlled assumption is varied in an isolated branch?
- Can a colleague inspect and reproduce the experiment without relying on the original operator's machine?

This is the product hypothesis to validate with external users.

## 2. Initial customer segment

### Beachhead: simulation and engineering R&D teams using Python

Prioritize teams that already build or maintain event-driven models and have a recurring need to reproduce difficult outcomes, compare scenarios, or explain how a result was reached.

Potential first users:
- simulation engineers and Python model developers;
- university and independent research laboratories;
- engineering R&D teams building digital experiments;
- reliability and systems engineers who use event-driven models for controlled analysis.

Do not initially sell Chronos as a replacement for a full commercial simulation suite, a workflow orchestration platform, a distributed database, or a production observability platform.

### Customer problem to test

The team can run a simulation, but preserving the exact initial conditions, inputs, causal history, and reproducible branch comparisons is cumbersome or implemented inconsistently across projects.

The first customer interview should establish:
1. how often this problem occurs;
2. the cost of a non-reproducible or poorly explained run;
3. what tools and internal scripts are used today;
4. what evidence is required before a team trusts a replay;
5. who owns the budget and approves a pilot.

No market-size, conversion, or willingness-to-pay claim is established yet.

## 3. First commercial offering

### Chronos Experiment Workbench — proposed product name

The first sellable offer should be a **developer-focused experiment toolkit**, not a hosted multi-tenant platform.

Proposed initial package:
- the Python engine and documented public APIs;
- a command-line workflow for creating, validating, replaying, and comparing experiment artifacts;
- a small set of realistic, executable reference experiments;
- portable experiment bundles containing declared inputs, version metadata, event history, branch lineage, and replay-verification results;
- human-readable run and branch comparison reports;
- onboarding and integration support for a customer's existing Python model.

The current repository provides parts of this foundation, including the Python engine, serialization and replay APIs, timeline continuations, and a supply-resilience reference experiment. The CLI, polished reports, artifact-bundle contract, and customer-facing workbench experience are proposed work, not completed features.

### Explicitly out of scope for the first offer

- hosted multi-tenant execution;
- claims of exactly-once side effects;
- automatic sandboxing of arbitrary replay handlers;
- distributed consensus or leader election;
- certified or universally accurate physical simulations;
- physical time travel, quantum temporal effects, or closed timelike curves.

These would expand the security, reliability, and scientific burden before the core customer problem is validated.

## 4. Product experience and acceptance criteria

A first-time evaluator should be able to:

1. install Chronos in a clean supported Python environment;
2. run a documented example without network access or paid infrastructure;
3. inspect the initial state, inputs, event history, and declared causal links;
4. export a portable experiment artifact;
5. replay it in a fresh process;
6. see an explicit pass/fail result for history and state verification;
7. create two isolated branches from one checkpoint;
8. compare the resulting states and explain which input changed the outcome;
9. reproduce the workflow from the documentation without maintainer intervention.

The public demo must use the real engine and real persisted artifacts. It must not simulate success with fabricated dashboard values or imply that a visual mock-up is a functioning product.

## 5. Commercial model to validate

Do not lock in subscription pricing before customer discovery. Test the following sequence:

**First revenue path**
- paid technical evaluation or scoped pilot;
- integration and model-porting assistance;
- training and team onboarding;
- support and maintenance agreement where the customer needs it.

**Potential later product revenue**
- commercial workbench/reporting experience;
- team collaboration and controlled artifact management;
- enterprise deployment support and integrations;
- service-level commitments only after the operating model can actually support them.

Any tier boundaries, price points, hosting promises, or service levels require customer evidence and cost analysis before publication.

## 6. Competitive position

Chronos should compete on a narrow workflow: reproducible causal experiments across alternative logical timelines.

It should not claim broad superiority over SimPy, salabim, AnyLogic, or Temporal. These products have different purposes and mature capabilities. Chronos must demonstrate a useful complementary workflow and publish fair, versioned comparisons only where semantics and workloads are comparable.

The competitive proof programme is maintained in [competitive-positioning.md](competitive-positioning.md).

## 7. Trust and release requirements

Before a paid pilot involving customer data or important engineering decisions:
- document the threat model and replay trust boundary;
- define the supported Python and operating-system matrix;
- settle the public API and compatibility policy for the pilot surface;
- test artifact parsing, tampering detection limits, interrupted persistence, and recovery;
- state clearly that SHA-256 digests are reproducibility checksums, not signatures or proof of authenticity;
- document that replay invokes registered handler code and is not a sandbox;
- document at-least-once worker behavior and TLS/key-management requirements if worker messaging is used;
- provide data handling, retention, deletion, and incident-contact terms appropriate to the pilot;
- run customer-specific acceptance tests before making deployment claims.

A passing CI matrix is necessary engineering evidence, not a substitute for security review, customer acceptance, or production operations.

## 8. Customer discovery programme

The first validation cycle should aim for:
- 10 structured conversations with simulation, research, or engineering R&D practitioners;
- 3 design partners willing to test a real workflow;
- 3 independent clean-environment reproductions of the public reference experiment;
- at least 1 scoped pilot proposal based on a named customer problem.

These are programme targets, not completed traction or commitments.

Record the customer's current workflow, pain severity, required integrations, trust requirements, buying authority, and the exact success criteria for a pilot. Do not count general interest or repository stars as product validation.

## 9. Launch gates

### Gate A — credible public evaluation
- current full CI matrix passes on the release candidate;
- install and quickstart verified from built artifacts;
- executable reference experiment and clean-process replay;
- public API status and known limitations documented;
- no unresolved critical correctness or security defect.

### Gate B — polished commercial launch
- coherent product website and real end-to-end demo;
- clear product brief, architecture, security/trust page, roadmap, and support contact;
- customer onboarding and pilot statement-of-work template;
- customer data handling and support expectations documented;
- at least one external user has reproduced the reference workflow;
- claims are backed by evidence and clearly bounded.

### Gate C — production deployment profile
- deployment-specific architecture and threat model;
- backup/restore, retention, monitoring, incident response, and upgrade runbooks;
- independent security review appropriate to the deployment;
- load, failure-injection, and recovery acceptance tests;
- written customer acceptance.

A polished launch does not require pretending Gate C is complete. Chronos can launch as a carefully labelled commercial early-access product after Gate B, while production suitability remains deployment-specific.

## 10. Ownership, licensing, and investment

The repository currently declares Apache-2.0. Preserve the existing license while the commercial model is validated; do not silently relicense existing code or imply that a proprietary license has been adopted.

Because the owner is open to strategic investment, prepare for diligence without promising equity or control:
- maintain clear ownership and contributor records;
- retain dependency and license notices;
- document IP provenance and any third-party contributions;
- keep financial, product, and technical claims evidence-backed;
- evaluate any investment by valuation, dilution, governance, IP rights, exclusivity, and operational obligations.

No equity, exclusivity, IP assignment, or change of control should be agreed to without explicit review and approval.

## 11. Immediate execution order

1. Finish the current correctness and cross-platform CI cycle.
2. Resolve the public API and captured-record ownership contract.
3. Turn the existing supply-resilience experiment into the canonical customer demo, with fresh-process artifact replay and branch comparison.
4. Build a minimal CLI and portable experiment report around existing public APIs.
5. Complete the security/trust model and pilot data-handling terms.
6. Conduct customer discovery and recruit design partners.
7. Build the commercial website and investor/customer materials from verified product behavior.
8. Run a scoped pilot before promising a hosted or enterprise deployment.

**Decision rule:** prioritize work that makes a real customer workflow easier to reproduce, inspect, compare, or trust. Do not add speculative features merely to make the feature list look larger.
