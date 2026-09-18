# Scientific semantics

- `coordinate_dd` reports predictive dynamical self-containment, not an intervention effect.
- `solve_forest_cut` and `solve_treewidth_cut` are exact for the directed incoming-cut surrogate.
- `optimise_multistart` reports first-order stationarity only.
- `solve_branch_bound` is exact only for its supplied objective and valid lower-bound contract.
- worst-case and CVaR routines make no inherited-submodularity assumption.
- fixed-horizon trajectory DP is exponential in the horizon; the unrestricted variable-horizon forest boundary remains open.
- no negative or failed experiment is removed by the software layer.
