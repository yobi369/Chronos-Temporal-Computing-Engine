# Finite-trace temporal logic and bounded model checking

Chronos provides a small temporal-logic evaluator over finite traces.

- Atom: state predicate.
- Not, And, Or: Boolean composition.
- Next: strong next; false at the final position when no next state exists.
- Always: operand holds at every remaining position.
- Eventually: operand holds at some remaining position.
- Until: left holds continuously until right becomes true; right must become true within the finite trace.

The bounded model checker explores a caller-provided transition relation breadth-first and checks formulas over all paths to the requested depth. Deadlocked states are extended by stuttering. State identity uses canonical JSON content. The caller must provide a finite state representation and explicit depth/state limits.

A counterexample is a concrete state trace within the explored bound. A passing result means only that no counterexample was found in the explored finite graph and depth. It is not an unbounded proof, proof for infinite-state systems, or evidence about physical reality.
