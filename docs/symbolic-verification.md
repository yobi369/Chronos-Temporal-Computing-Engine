# Symbolic predicates and bounded verification

Chronos now provides a small symbolic expression language:
- `Field` and `Literal`;
- `Compare` for equality and ordered comparisons;
- `Boolean` for conjunction, disjunction and negation.

`symbolic_bounded_check` evaluates an invariant over all reachable explicit states up to a depth bound. It reports a counterexample trace and enforces independent state and generated-path budgets.

`canonical_independent_trace` canonicalizes action-label sequences under adjacent swaps declared independent by the caller. The correctness of that independence relation is the caller's responsibility. It is a trace equivalence utility, not a sound partial-order reduction engine for arbitrary temporal properties.

This is symbolic predicate evaluation over finite explicit states, not a BDD, SAT, SMT or theorem-proving backend. There is no proof beyond the supplied finite transition system and bounds.
