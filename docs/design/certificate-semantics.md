# Certificate semantics

The four layers describe algorithmic bounds, numerical assertions, statistical
assertions and economic declarations. Internal consistency is distinct from
authenticating those declarations against external evidence.

The composed expression is `(U - L) + 2 * (numerical + statistical + cost
+ valuation discrepancy)`. Local dev6 retains the dev3 repair and calculates it exactly over the supplied
integer/binary64 operands and displays its least finite binary64 upper endpoint.
A large bound can remain internally consistent but vacuous. An absent incumbent
has no regret bound and does not establish infeasibility. Non-finite aggregates,
contradictory supplied summaries, unenclosed non-exact layer claims and missing
E2/E3 currency/base-date declarations are refused.

This layer route does not establish that an enclosure, population event or
valuation is genuine. The legacy CLI keeps `certificate_verified=false`.
See [the SD2 contract](../P10_SD2_COMPOSITIONAL_CONTRACT.md).
