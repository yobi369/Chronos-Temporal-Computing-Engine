# Temporal model and terminology

## Logical time

A non-negative integer coordinate used to schedule simulated events. Its unit is defined by the experiment (for example, milliseconds, simulation steps, or abstract ticks). It is not automatically UTC or physical elapsed time.

## Execution order

The engine dispatches events by ascending logical time, then ascending insertion sequence.

## Causal relation

An optional parent link records declared event provenance. It is not proof of physical causation; a model can omit dependencies.

## Lamport clock

The logical clock supports local tick and remote-observation operations. It captures ordering constraints, not duration or wall-clock synchronization.

## Branching timelines

A branch is a counterfactual computational continuation from a captured state. Divergence between branches describes model outcomes, not alternate physical universes.

## Research extensions

Potential work includes vector clocks, temporal logic, persistent event sourcing, deterministic replay, interval time, hybrid continuous/discrete simulation, and model checking. Each extension needs explicit semantics and tests before being claimed as supported.
