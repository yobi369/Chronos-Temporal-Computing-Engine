# Competitive positioning and proof programme

**Status:** strategic hypothesis and validation plan. This is not a claim that Chronos currently outperforms the products named here.

## The market reality

Chronos enters an established category, but the products below solve different primary problems:

| Product/category | Established strength from public documentation | What Chronos must prove |
|---|---|---|
| [SimPy](https://simpy.readthedocs.io/en/stable/) | Python process-based discrete-event simulation, resource/congestion modeling, and manual or real-time stepping | That causal provenance, versioned histories, replay verification, and branch continuation solve a distinct workflow—not merely duplicate a scheduler |
| [salabim](https://salabim.org/manual/) | Python discrete-event simulation with queues, resources, stores, statistical monitoring, and animation | That Chronos complements or outperforms it for reproducible causal experiments; do not claim broader modeling or visualization capability |
| [AnyLogic](https://www.anylogic.com/features/) | Commercial multimethod simulation: discrete-event, agent-based, and system dynamics, plus experiment frameworks | Do not compete feature-for-feature with its mature visual modeling, libraries, and enterprise ecosystem; identify a narrow Python-native workflow where Chronos is demonstrably useful |
| [Temporal](https://docs.temporal.io/temporal) | Durable execution of application workflows, persisted histories, deterministic replay, and recovery across failures | Explain the distinction: Chronos is a simulation/research engine, not a durable workflow service or fault-tolerant orchestration platform |

These products are not interchangeable benchmarks. Their goals, runtimes, APIs, and deployment models differ. Any comparison must name exact versions, workloads, configuration, hardware, and evaluation date.

## The proposed Chronos wedge

The strongest defensible product hypothesis is:

> **A Python-native environment for reproducible causal experiments across alternative logical timelines—with explicit provenance, recorded inputs, verified replay, and inspectable branch histories.**

It should make it easy to answer:
1. What exact inputs and initial state produced this result?
2. Which events caused a particular state transition?
3. Can an independent operator replay the run and verify its history and final-state digest?
4. What changes when one controlled assumption is altered in a fork?
5. Can branches be compared without mutating the parent experiment?
6. Can another researcher reproduce the experiment from an exported artifact and documented handler version?

This is a hypothesis, not yet proven market advantage. The differentiator must be the complete experiment lifecycle and the quality of its evidence—not a long feature list.

## Target users and first use cases

Prioritize narrow, testable adoption paths:
- **Research and teaching:** reproducible experiments, event provenance, alternative scenario branches, and portable experiment records.
- **Simulation developers:** debugging causal event sequences, comparing controlled parameter changes, and regression-testing model behavior.
- **Engineering R&D teams:** deterministic reproductions of complex event-driven behavior before integrating a model into a larger system.

Do not initially promise a complete replacement for AnyLogic, SimPy, salabim, or Temporal. Integration and interoperability may be more credible than replacement.

## Competitive proof programme

No performance or superiority claim is publishable until evidence exists.

### 1. Reproducibility benchmark
Publish shared, version-controlled workloads; exact runtime, dependency, OS, CPU, memory, and configuration metadata; warmups, repeated trials, raw samples, variance/uncertainty, and memory use. Measure scheduler throughput/latency separately from serialization, persistence, replay, forks, and causal queries. Compare only where semantics map fairly; report "not comparable" otherwise.

### 2. End-to-end workflow benchmark
Build a public reference scenario (for example, a network/service outage or constrained logistics system) and demonstrate:
- deterministic baseline run;
- event-level causal explanation of a selected outcome;
- persisted run artifact;
- fresh-process replay with history and digest verification;
- two isolated forks with one controlled input change;
- machine-readable branch comparison;
- reproduction by a second operator using only the artifact and documented instructions.

### 3. Reliability evidence
Add failure-injection coverage for malformed/truncated artifacts, schema mismatch and migration, interrupted persistence, handler exceptions/retry semantics, duplicate or reordered worker messages, authentication failures/key rotation, replay drift/digest mismatch, and concurrent access against the documented single-writer contract. Separate tested guarantees from filesystem, network, and deployment assumptions.

### 4. Adoption evidence
Before declaring product-market fit, obtain external users who are not repository contributors, at least three independent reproduction attempts, feedback from researchers or simulation practitioners, and evidence that users choose Chronos for its causal/branch/replay workflow rather than novelty alone.

## Claims policy

Allowed today, subject to documented constraints: deterministic discrete-event simulation; causal event provenance and logical-clock support; isolated logical-timeline forks; versioned event histories and replay verification; experimental hybrid, uncertain-time, bounded-verification, and worker capabilities with their stated limitations.

Not allowed without new implementation and independent evidence:
- "faster than SimPy/AnyLogic/Temporal";
- "more reliable than established simulation platforms";
- "production-grade distributed simulation";
- "exactly-once execution" or "tamper-proof audit trail";
- "scientifically validated model of physical time";
- blanket "enterprise-ready" claims.

## Strategic success criterion

Chronos stands out when an external user can take a real event-driven problem, build a model, preserve its exact experiment record, explain causality, branch alternative assumptions, replay in a clean environment, and independently verify the evidence—with less friction or materially better traceability than their current workflow.

That outcome is the product. The codebase, tests, documentation, examples, benchmarks, release artifacts, and support process must all reinforce it.
