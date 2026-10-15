# CDRS-E 0.1.0rc1 — publication-durable software-only release candidate

**Author and maintainer: Antonio Clim. Apache-2.0 applies to the software-only surface. Canonical repository: `https://github.com/antonioclim/cdrs-e`.**

This working version implements the P6B stored-input weighted-cut contract.
`solve_forest_cut`, `solve_treewidth_cut`, `solve_exhaustive(problem)` and
`solve_branch_bound(problem)` use rational arithmetic for the stored matrix and
weights. Binary64 matrix entries are embedded as their exact dyadic values; this
does not recover an intended decimal or an unobserved physical coefficient.
Budget dynamic programmes require exactly integral activation costs and budgets.
Omitting a budget means a non-binding total-cost budget.

## Publication identity and archival metadata

The canonical repository identity is `https://github.com/antonioclim/cdrs-e` and the release-candidate tag is `v0.1.0rc1`. `CITATION.cff`, CodeMeta and `pyproject.toml` carry this durable identity. No DOI is fabricated or embedded in this source snapshot. If an archival record later assigns a DOI, that external record or a subsequent source revision should carry it without rewriting the frozen source tag. Security reports should follow `SECURITY.md`; ordinary defects and contribution proposals should follow `CONTRIBUTING.md`.

## Installation and a replayable example

From this source directory, in a Python environment containing its declared
scientific dependencies:

```text
python -m pip install --no-build-isolation --no-deps .
python -m cdrse self-check --json
python -m cdrse solve-forest examples/forest_problem.json --output result.json
python -m cdrse verify-result examples/forest_problem.json result.json
```

The example selects `[0, 2]` with objective 5. `--output` is accepted before or
after the subcommand. A wheel and source distribution are delivered separately
in the phase package; this directory does not require a nonexistent local wheel.
Dependency installation on another machine is a separate environment step.

## Exact results, callback evaluations and limits

The legacy result exposes floating-point display fields. Its
`metadata.result_contract` (or Python `result.to_record()`) carries authoritative
rational numerators and denominators, the objective and full problem digest,
incumbent, bounds, counters and termination. Outward-rounded legacy bound fields
must agree with that record. `verify-result` independently enumerates the small
finite model, checks its inequalities and also detects inconsistent display
fields. Its default ceiling is 16 vertices; it is not a scalable proof checker.

A user-supplied numerical callback has `exact=False`, `certified=False` and an
`UNCERTIFIED_EVALUATION` record. Zero declared error is not proof of an exact
oracle. Legacy bounds for that mode are diagnostics, not validated enclosures.
Floating-point DD and high-precision DD retain their numerical status.
`verify-certificate` checks consistency of the older layer container only;
it explicitly does not replay a problem or verify an optimisation certificate.

B&B accepts `max_nodes`, `max_calls` and `time_limit`. All oracle calls, including
the single seed evaluation, count towards `max_calls`. Time limits are
cooperative and cannot pre-empt a callback already running. With no feasible
incumbent the selection and upper bound are absent. A stopped search is never
labelled infeasible merely because it has not found a solution.

Scenario callbacks and floating-point dynamic solvers do not return a rigorous
numerical exactness guarantee. The scaled-integer min-cost-flow routine retains
its separately stated transformed-cost scope. The trajectory construction is
fixed-horizon/XP-type with explicit resource counters, not FPT in the horizon
alone. Grassmann multistart gives stationary candidates, not global optima.

## Verification evidence and current limits

The fresh rc1 execution authority is P10-SD34 and the latest integrated checkpoint is P10-SD35. Source and installed suites previously returned 1,280/1,280. QUICK passed. The initial parent FULL orchestration was interrupted and remains recorded as interrupted; 28/28 independently completed shards were subsequently reconciled, yielding `PASS_WITH_ORCHESTRATION_QUALIFICATION`. The interrupted parent attempt is not relabelled as a pass.

P10-SD37 was the packaging and licensing-surface remediation that removed every public path rooted at `paper/`, `evidence/`, `provenance/` or `reports/`. P10-SD39 prepared a publication-durable transition draft but was not promoted because the package module docstring still described the candidate as private. P10-SD40 applies the explicitly authorised one-line docstring correction, preserves the other 28 registered files byte-identically, proves AST identity after removing the docstring and regenerates and retests the source archive, wheel and sdist. Private excluded material remains outside the public software surface.

No finite suite proves universal correctness. DS1 concerns the stored-cut implementation and does not validate DD on real sensors, population confidence coverage, financial value or global Grassmann optimisation. Zero false certificates is an observation in the finite executed catalogues, not a universal guarantee or an undiscovered-defect probability. The original Phase XXXI named-sensor gate remains `FAIL_REAL_NAMED_SENSOR_GATE`. Phase XLIV remains invalid as scientific execution evidence. TS0 is not met, F03 and F15 remain open and programme completion is false.

Apache License 2.0 applies only to the software surface described in `LICENSING.md`. Operational publication authority is deliberately not encoded in this source tree. This source snapshot embeds no DOI and makes no claim that a Zenodo record, PyPI publication or journal submission forms part of the software artefact.

## P10 result and input contract repair

`verify-result` checks every defined top-level assurance field against the
authoritative record, including regret, proof state, termination and absent
incumbent bounds. The public regret is the upward-rounded authoritative rational
regret, not a subtraction of two rounded display endpoints. Unknown top-level
assertions are rejected. Additional metadata are explicitly listed as unverified.
Counter domain checks and agreement of the two mirrored counters do not
authenticate an execution log or proof-reference identity.

For unenclosed callbacks, numerical objective and optimality claims remain
uncertified. Finite service-family infeasibility is a separate check: it requires
no evaluation of the callback. A stopped callback with no incumbent has canonical
`NO_INCUMBENT` status; completed infeasibility has `PROVED_INFEASIBLE` termination.

The direct Python parser preserves input types until validation. Cardinalities
accept integers, excluding booleans, fractions and numeric strings. Endpoint
flags require booleans. The source test changes update only three version-identity
assertions and add the preserved P10 obligations and boundary controls.
No scientific threshold or original numerical test expectation is weakened.

## P10-SD2 compositional-layer repair (promoted in dev3 and retained in dev6)

The separately audited SD1 patch is included in `DecisionCertificate`. Its
composed expression is calculated exactly for the supplied integers and stored
binary64 operands, then displayed at the least finite binary64 upper endpoint.
Non-finite aggregate endpoints are refused. Boolean flags, coordinate indices,
incumbent availability and explicitly supplied derived summaries are checked
without lossy coercion. This does not authenticate the underlying problem,
statistical event or valuation. `verify-certificate` remains a legacy layer
consistency check with `certificate_verified=false`; `verify-result` is separate.

The original 477-case suite (including protected P3 cases) and the unchanged
280-case SD1 suite are the promotion obligations. Their observed dev3 results
are in the accompanying SD2 qualification records, not in historical R1 logs.
R1 coverage and mutation measurements describe dev2 only and do not quantify
dev3. No clean-machine, universal-correctness or publication claim is made.

## P10-SD4 economic frontier and finite-scenario repair (promoted in dev4 and retained in dev6)

The hash-bound SD3 patch is promoted without changing its two repaired modules.
Finite mean, worst-case and equiprobable empirical CVaR aggregation evaluate the
accepted integer and stored binary64 operands exactly, then convert once to the
nearest finite binary64 display. The display is not an outward enclosure and
does not authenticate a callback, probability model or valuation. Explicit
probability vectors remain unsupported for CVaR. Mean weights that pass the
existing near-one check are used as supplied rather than silently normalised.

`pareto_front` uses exact supplied coordinates for strict dominance.
`supported_points` expects a nondominated front and returns extreme lower-hull
representatives; it does not promise every duplicate label or collinear point
that ties along a supporting segment. The robust finite enumerator validates its
configuration before callback evaluation, compares exact aggregates before the
display conversion and retains `exact=false` and `certified=false`. E0 synthetic
regressions do not create E1 measurements or E2 monetary evidence.

The promotion suite contains the preceding 757 obligations, the byte-preserved
422-case SD3 suite fixed before the patch and the separately identified one-case
CVaR refinement added after the initial 11/12 designed-mutation result. These
1,180 case identities are finite, correlated software obligations, not
independent empirical replications or a probability of universal correctness.
R1 global coverage and mutations remain dev2 metrology; the SD3 two-module
coverage and mutation records retain their bounded historical scope.

## P10-SD10 corrected upstream-provenance source candidate (historical)

SD10 established the coherent source-only dev7 candidate and retained dev6 as the last qualified distribution/runtime identity at that boundary. The private historical provenance objects are excluded from this public software-only tree. Their scoped conclusions are represented only through current public release-engineering records under `release/`. See `docs/P10_SD9_UPSTREAM_PROVENANCE_CONTRACT.md` and `docs/P10_SD10_CANDIDATE_INTEGRITY_CONTRACT.md`.

## P10-SD8 deterministic build-envelope closure (local dev6)

Dev6 retains all qualified dev5 source and behavioural repairs and promotes the F35 build-closure remedy. The build backend is pinned to setuptools 82.0.1 and the build script enforces `SOURCE_DATE_EPOCH=1789430400`. The six-case SD8 regression lock raises the ordinary source suite from 1,203 to 1,209 finite correlated obligations. Local wheel/sdist byte identity is qualified only for the recorded recipe. The captured backend wheel is not upstream-authenticated and no independent-machine or multi-platform reproduction is claimed. See `docs/P10_SD8_BUILD_CLOSURE_CONTRACT.md`.

## P10-SD6 source-boundary and source-closure hardening (local dev5)

The hash-bound SD5 patch is promoted without changing its seven repaired modules or its 23-case test file. `ExactRationalBackend.directed_cut` now requires canonical unique integer indices in range. Exact witness domains are decided rationally. Coordinate-DD endpoint shortcuts validate a finite positive tolerance. Direct Python models reject boolean numerical fields and textual numerical arrays, while canonical hashing requires textual mapping keys.

The protected eight-case P3 regression file is now part of the ordinary test tree and source archive. The private K2 source candidate therefore collects all 1,180 historical obligations without borrowing that file from K3. The unchanged 23-case SD5 lock raises the dev5 promotion suite to 1,203 case identities. These are finite correlated software obligations, not independent empirical replications.

The dependency, security and type-contract utilities create their report directory on a pristine extraction and explicitly describe their bounded checks. They do not establish a complete transitive advisory scan, taint analysis, native-extension audit or clean-machine reproduction. See `docs/P10_SD6_SOURCE_BOUNDARY_CONTRACT.md`.



## P10-SD12 upstream-backed local dev7 qualification

The exact `setuptools 84.0.0` and `pip 26.2.1` wheel bytes used by the P10-SD12 build were recovered from official PyPA release workflow artefacts and locally matched to the SHA-256 values bound from official PyPI metadata. The dev7 wheel, sdist, immutable runtime and declared QUICK/FULL replays are qualified only in the recorded local CPython 3.13 Linux x86_64 scope. This is not an independent-machine or multi-platform reproduction. At the P10-SD12 checkpoint, publication and deposition had not been executed; that statement is historical rather than a current release gate.


## P10-SD32 Apache-2.0 rc1 promotion

P10-SD32 established the `0.1.0rc1` identity and local Apache-2.0 software-licence decision. The scientific implementation inherited from dev7 was unchanged except for explicit release-identity surfaces.

## P10-SD34/P10-SD35 qualification and integration

P10-SD34 is authoritative for the fresh rc1 QUICK/FULL, DS1, solver, CLI, formal and coverage evidence. P10-SD35 is the latest integrated documentary checkpoint. Their finite findings retain their stated scope and do not close TS0, F03 or F15.

## P10-SD37 software-only re-freeze

P10-SD37 removes all deferred-content path classes from the proposed public repository and release assets, preserves the scientific source byte-for-byte, repairs current qualification metadata and reconstructs deterministic release assets. The exact setuptools 84.0.0 backend was not re-executed in this isolated remediation environment; the assets are transparently derived by deterministic reassembly from the qualified SD35 wheel and sdist, followed by complete source and installed-wheel testing.

## Licensing scope

See `LICENSING.md`. Apache-2.0 applies to the software work; manuscript-facing and non-code content remains deferred.

## P10-SD40 bounded public-identity correction and full local re-freeze

P10-SD39 removed private remote-operation plans from the public source tree, assigned durable repository metadata and replaced operational authorisation flags with artefact-stable qualification fields, but its local draft was not promoted because `src/cdrse/__init__.py` still described the software as private. P10-SD40 changes only that module docstring from the private-candidate wording to `CDRS-E auditable research software release candidate.` No other byte in that file changes. The remaining 28 registered files are byte-identical to SD37 and the AST after removing the module docstring is identical. The CLI reports the release channel and canonical repository rather than a transient boolean describing whether a remote publication operation has occurred.
