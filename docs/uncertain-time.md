# Interval and uncertain-time semantics

TimeInterval represents a closed finite interval [lower, upper]. A definitely precedes B only when A.upper < B.lower. Overlap means neither interval is definitely earlier; it does not imply simultaneity. Intersection and hull are set operations.

possible_orders enumerates linear extensions of the definite-precedence relation for at most eight intervals. It deliberately does not choose an arbitrary total order for overlapping timestamps. This is a finite combinatorial utility, not a probability distribution over event times. Probabilistic timestamps, interval-valued event queue integration and uncertainty propagation through continuous solvers remain future work.
