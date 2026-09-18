# P10 public-result verification contract

The accepted finite verification result covers the stored weighted-cut problem
or finite service-family infeasibility. It does not authenticate how the solver
ran. The independent verifier repeats feasibility and objective enumeration
without importing a solver or the companion objective implementation.

## Authoritative and public fields

The rational result record is checked first. The public selected set, objective,
lower and upper bounds, upward-rounded regret, exact/certified flags, status and
termination must then agree. No-incumbent and infeasible states must carry null
incumbent objective/upper/regret displays. Infeasibility is verified by an empty
finite feasible family, never inferred from an interrupted search.

Two mirrored counters must match and all ten counters must be nonnegative
integers. These are domain/equality checks, not proof of execution. Additional
metadata are enumerated in the verifier response as unverified; unknown public
assertions outside metadata are refused. Proof-reference strings are not
authenticated by the arithmetic verifier.

Unenclosed callbacks retain diagnostic-only display bounds and uncertified
numerical values. Infeasibility, which concerns the service family alone, can
be independently certified even when that unused objective is a callback.

The exact result may use any documented exact solver status alias. The verifier
certifies the finite optimum and consistent state, not the provenance of a
particular forest or tree-decomposition computation.
