# Canonical optimal-witness policy

CDRS-E reports the **lexicographically smallest sorted coordinate tuple** among all feasible selections that attain the same declared objective value. The policy applies to the exact stored-rational static backends: exhaustive enumeration, forest dynamic programming, treewidth dynamic programming conditional on a valid decomposition and exact branch-and-bound.

The objective value remains primary. Activation cost, incoming-cut loss and search order are not secondary tie-breakers unless they already contribute to the declared weighted objective. This matters when `cost_weight = 0`: lower activation cost does not become an undeclared tie-breaker.

The policy makes witness identity reproducible across exact backends. It does not assert uniqueness of the mathematical optimum. Callback and floating-point dynamic routes retain their documented numerical contracts and do not acquire exact stored-input authority from this policy.
