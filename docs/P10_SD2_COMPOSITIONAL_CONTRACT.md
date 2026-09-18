# P10-SD2 compositional-layer contract

Version: `0.1.0.dev3`. Author: Antonio Clim. Local candidate, not a public release.

`DecisionCertificate` is the legacy layer container, not the rational
stored-cut `ResultRecord`. For a supplied incumbent and finite validated
operands it forms `U - L + 2*(numerical_error + statistical_error + cost_error
+ valuation_error)` exactly over supplied integers and stored binary64 values.
It reports the least finite binary64 value greater than or equal to this
expression. If no finite upper endpoint exists, validation fails. This is
not a validated enclosure of an unprovided DD computation or physical input.

`non_vacuous` compares that conservative display with the supplied tolerance.
For very large integer tolerances this may refuse a mathematically admissible
boundary case; it cannot accept by using an endpoint below the exact expression.

`from_dict` validates the packaged schema and requires actual booleans,
non-negative integer coordinate indices (excluding booleans), coherent
incumbent availability and agreement of any supplied derived summaries.
`selected=None` with no incumbent has no regret bound and is not a proof
of infeasibility. A present, internally coherent empty selection is permitted
by this layer contract; external problem feasibility is not authenticated.

`verify-certificate` reports `certificate_verified=false` even after the
layer checks pass. The problem digest, oracle/enclosure flags, statistical
assertions and economic declarations are supplied assertions, not newly
authenticated evidence. E0 fixtures remain synthetic. `verify-result`, its
rational result contract and the stored-cut solvers have not been changed.

SD1 found 225 correlated failures in its 280-case frozen baseline suite and
passed all 280 after the component patch. Its initial 7/8 designed-mutation
record and separate survivor-detection refinement remain historical. SD2
qualification records identify the actual versioned source and distributions.
Neither finite suite establishes a global defect probability.
