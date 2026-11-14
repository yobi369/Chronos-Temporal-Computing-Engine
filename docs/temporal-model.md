# Temporal model and terminology

## Logical time

A non-negative integer coordinate used to schedule simulated events. Its unit is defined by the experiment (for example, milliseconds, simulation steps, or abstract ticks). It is not automatically UTC or physical elapsed time.

## Execution order

The engine dispatches events by ascending logical time, then ascending insertion sequence. This defines deterministic scheduler order for a fixed sequence of submitted inputs and deterministic handlers.

## Causal relation and provenance

An optional parent link records declared event provenance. The causal graph supports ancestor and descendant queries over those declared links. It is not proof of physical causation; a model can omit dependencies or declare incorrect ones.

## Lamport clock

The Lamport-style logical clock supports local tick and remote-observation operations. It captures ordering constraints, not duration or wall-clock synchronization.

## Vector clocks

Vector clocks represent distributed happens-before ordering without assuming a globally synchronized physical clock. If one vector is componentwise no greater than another and is strictly smaller in at least one component, it precedes the other. If neither vector precedes the other, the observations are concurrent under the vector-clock model. These are computational ordering semantics, not physical-time measurements.

## Branching timelines

A branch is a counterfactual computational continuation from a captured state. Each fork is isolated from the source timeline and sibling forks. Divergence between branches describes model outcomes, not alternate physical universes.

## Implemented computational extensions

The repository also contains versioned snapshots and in-memory v1-to-v2 migration, canonical versioned event logs, payload contracts, bounded local persistence, deterministic replay, final-state digest comparison, finite-trace temporal operators, bounded explicit-state model checking, interval-time scheduling, hybrid RK4/discrete-event coupling, and a durable at-least-once worker protocol. Their assumptions and limitations are documented in the corresponding guides and validation strategy.

## Research directions and boundaries

Potential future work includes broader distributed membership and partition semantics, stronger multi-process reproducibility, independently validated numerical methods, and additional formal verification techniques. These require explicit semantics, tests, and independent evaluation before being claimed as supported.

Relativistic time dilation, quantum temporal models, closed timelike curves, and other speculative physical ideas are not implemented. Any future physical claim would require precise equations, units, assumptions, provenance, and comparison with established reference results.
