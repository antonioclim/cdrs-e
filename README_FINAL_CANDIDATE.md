# CDRS-E 0.1.1 — research software release (local candidate)

Author and maintainer: Antonio Clim. Contact: Antonio.clim@csie.ase.ro. ORCID: https://orcid.org/0000-0003-4745-0431.
Canonical repository: https://github.com/antonioclim/cdrs-e.

## Source identity and current assurance

This local candidate prepares normal version `0.1.1`, with status `PREPARED_RELEASE_011`. It is not published. It addresses the five QA2 software findings: CLI error contracts, selected-run Grassmann status, backend parameter validation, wheel licence binding and installed-module provenance. See [QA2 scope](docs/QA2_0_1_1_SCOPE.md).

The immediate predecessor is public `0.1.0`, commit `b8333fb0b72f6b07c4fd1fa4969d0704c48b12f7`, tree `17c208e9909b097c07ba7bb84991b94231eea819`, source-archive SHA-256 `061e5e3412bbb6335a4b9aa28dd54595faf866a6487359429a808be0e6a05c86`. Its recorded software DOI is https://doi.org/10.5281/zenodo.23535035. These predecessor identifiers are retained records, not a new online inspection. No commit, tag, publication date or DOI is invented for 0.1.1.

The source metadata are frozen before finite QA2 validation. Their UNRUN fields describe that freeze; later execution evidence must bind these exact bytes externally. Targeted finite success, if demonstrated, does not mean full-suite or global scientific qualification. Original public 0.1.0 and all earlier results remain intact.

The associated manuscript is *Which Channels Should We Keep? Uniform Bounds for Cut-Based Selection in Gaussian Vector Autoregressions*. Its R1.6 editorial identity is separate and derives from the verified v15 corpus, not a recovered V5.1. No manuscript files, article figures, private wrappers or raw third-party datasets are included.

## Installation and a replayable example

Select the intended version and verify its source/distribution digest before installation. A default-branch download is not a substitute for a tagged version. The following are instructions for a separately authorised execution with the declared scientific dependencies already available:

```text
python -m pip install --no-build-isolation --no-deps .
python -m cdrse version
python -m cdrse solve-forest examples/forest_problem.json --output result.json
python -m cdrse verify-result examples/forest_problem.json result.json
```

The retained example expects selection `[0, 2]` and objective 5. These are example expectations, not a report of a new execution in this source snapshot. `--output` is accepted before or after the subcommand. Full validation and administrative packaging checks are specified in [docs/RC3_VALIDATION_PLAN.md](docs/RC3_VALIDATION_PLAN.md).

## Mathematical and computational scope

The four exact static backends solve the declared stored-input weighted incoming-cut objective under their validated model and structural prerequisites. Binary64 inputs are embedded as exact dyadic values, without recovering an intended decimal or a physical coefficient. Budget dynamic programmes require integral activation costs and budgets. A missing budget means a non-binding total-cost budget.

The authoritative rational result contract is distinct from floating-point display fields. `verify-result` enumerates a supported finite family with default ceiling 16 vertices; it is not a scalable proof checker. `verify-certificate` remains a legacy layer-consistency check with `certificate_verified=false`. Numerical callback evaluation remains uncertified. Generic numerical DD enclosure, population coverage, global Grassmann optimality, independent-host reproduction and new raw-data campaigns are not established by this preparation.

Canonical witness selection, endpoint checks, counters, bounds and interruption statuses retain version-specific contracts. An interrupted search without an incumbent is not a proof of infeasibility. Time limits are cooperative and cannot pre-empt a callback already running. Exact supplied-operand aggregation is separate from validating a scientific or monetary model.

## Verification and release engineering

This is a local 0.1.1 candidate intended for a normal release, not a published release. Publication, tag creation and online mutation are separate decisions. Public0.1.0 remains unchanged; its literal source profile is retained under `release/history/public_0_1_0/` and in the baseline archive.

The frozen source records execution status before the bounded QA2 phase. Consult the separately delivered, hash-bound QA2 evidence for any subsequent targeted tests, baseline witnesses, distributions and installation-origin checks. The complete source suite, coverage qualification, multi-platform validation and empirical campaigns are not implied. The retained full validation pipeline remains UNRUN unless separately evidenced. No finite suite proves universal correctness.

The manual-only Actions workflow and legacy full-validation helpers are retained with current version guards. They are not started or qualified by this source preparation. Historical mutation classification remains outside the QA2 phase.

## History and limits

Historical rc1/rc2 records and their source hashes remain unchanged. The original public 0.1.0 preparation profile is under `release/history/public_0_1_0/`; old normal-release notes describe that predecessor. Historical D2 and Component C records do not transfer a complete PASS to 0.1.1.

Programme REWORK, H-02 FAIL, H-14 FAIL, scientific Q12 and recorded scientific limitations retain their identities. STOP33/A156, G0 BLOCKED, HOLD and the unrecovered historical receipt remain unchanged. No new scientific campaign or mathematical-proof check is claimed.

## Licensing and attribution

Apache-2.0 applies to the included software surface defined by `LICENSING.md`, with individual exceptions retained. Manuscript, figure, evidence, private-provenance, third-party data and third-party content rights remain separate. Operational publication authority is deliberately not encoded in this software tree. `LICENSE` and `NOTICE` are included in distributions.

AI assistance in source review and preparation is described in [docs/AI_ASSISTANCE.md](docs/AI_ASSISTANCE.md). Tool assistance is not an independent authority or formal verification. Security reports should follow `SECURITY.md`; ordinary defects should follow `CONTRIBUTING.md`.
