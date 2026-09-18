# P10-SD4 economic boundary and finite-scenario contract

Version: `0.1.0.dev4`. Author: Antonio Clim. Local candidate, not a public release.

## Arithmetic status

The helpers in `cdrse.economics` and the finite enumerator in
`cdrse.algorithms.robust` evaluate accepted integer operands and stored binary64
operands through their exact integer ratios. Public scalar outputs are converted
once to the nearest finite binary64 value. This prevents intermediate overflow,
underflow, cancellation and ranking by prematurely rounded displays. It is not
directed rounding, a validated enclosure, an authentication of the callback or
a statement about an intended decimal value not stored in the input.

Non-finite inputs, boolean or textual numeric coercions, malformed uncertainty
intervals and non-finite final displays are refused. Exact arithmetic can still
consume substantial resources; this contract provides no denial-of-service or
complexity guarantee.

## Scenario aggregation

Mean, worst-case and equiprobable empirical upper-tail CVaR are distinct modes.
CVaR requires `0 <= alpha < 1` and does not accept explicit probability vectors.
Mean probabilities must be non-negative, have the correct length and pass the
pre-existing near-one check; accepted values are used as supplied, not silently
renormalised. Worst-case aggregation is unweighted, although a supplied vector
is validated for interface consistency.

The robust enumerator validates mode, alpha, probability shape and scalar types
before evaluating any subset, including when the admitted family is empty. A
feasibility callback must return an actual boolean. Callback exceptions propagate
and are not converted into infeasibility. Exact aggregate values determine the
ranking before the final display conversion. The result continues to state
`exact=false` and `certified=false`, because the callback and model are not
authenticated and no numerical enclosure is supplied.

## Pareto geometry

`pareto_front` applies exact strict dominance to the supplied cost/loss pairs and
retains equal-coordinate nondominated labels. `supported_points` has a
nondominated-front precondition and returns the extreme representatives of the
exact lower convex hull. Collinear interior points and duplicate labels tied on a
supporting segment are not all returned. Therefore it is not a complete labelled
frontier routine. The manuscript result that positive scalarisation can miss
unsupported efficient points is unchanged.

## Evidence boundary

The 422-case SD3 suite was fixed before the two-module patch. One CVaR boundary
case was added separately after the initial mutation run to detect its retained
M05 survivor; its chronology remains explicit. Promotion retains the original
11/12 initial mutation result and does not relabel the refinement. All new values
are synthetic E0 inputs. No E1 measurement, E2 monetary amount, external
provenance, clean-machine reproduction, universal theorem proof or global defect
probability is supplied by this contract.
