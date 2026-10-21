# CDRS-E 0.1.0rc3 — prepared software-only release candidate

Author and maintainer: Antonio Clim. Contact: Antonio.clim@csie.ase.ro. ORCID: https://orcid.org/0000-0003-4745-0431.
Canonical repository: https://github.com/antonioclim/cdrs-e.

## Source identity and current assurance

This is the prepared `0.1.0rc3` source, with status `PREPARED_CANDIDATE_RC3`. Its build, tests, installation, coverage, mutation assessment and runtime checks are **UNRUN** in this preparation. Source review and syntactic checks do not establish execution or universal correctness. The current source includes separately documented runtime-contract and release-engineering corrections; earlier test counts are not assigned to these changed bytes.

The public predecessor is `v0.1.0rc2`, commit `c4bedf30c3b5967ade38b0aeac897529a67a7672`, software DOI https://doi.org/10.5281/zenodo.23409442. Historical rc1 retains https://doi.org/10.5281/zenodo.22841999. The proposed rc3 tag must identify the exact reviewed commit integrated into `main`; no rc3 commit, release date or version DOI is asserted here. Later publication and execution are established by external receipts bound to the actual source and artefact hashes. This file records preparation, not a live publication registry.

The associated manuscript is *Which Channels Should We Keep? Uniform Bounds for Cut-Based Selection in Gaussian Vector Autoregressions*. Its editorial R1.3 identity is separate from this software source. The source does not include manuscript files, article figures, private wrappers or raw third-party datasets.

## Installation and a replayable example

Select the intended version and verify its source/distribution digest before installation. A default-branch download is not a substitute for a tagged version. The following are instructions for a separately authorised execution with the declared scientific dependencies already available:

```text
python -m pip install --no-build-isolation --no-deps .
python -m cdrse version
python -m cdrse solve-forest examples/forest_problem.json --output result.json
python -m cdrse verify-result examples/forest_problem.json result.json
```

The retained example expects selection `[0, 2]` and objective 5. Those expectations are preserved; this preparation does not report a new execution. `--output` is accepted before or after the subcommand. Full validation and administrative packaging checks are specified in [docs/RC3_VALIDATION_PLAN.md](docs/RC3_VALIDATION_PLAN.md).

## Mathematical and computational scope

The four exact static backends solve the declared stored-input weighted incoming-cut objective under their validated model and structural prerequisites. Binary64 inputs are embedded as exact dyadic values, without recovering an intended decimal or a physical coefficient. Budget dynamic programmes require integral activation costs and budgets. A missing budget means a non-binding total-cost budget.

The authoritative rational result contract is distinct from floating-point display fields. `verify-result` enumerates a supported finite family with default ceiling 16 vertices; it is not a scalable proof checker. `verify-certificate` remains a legacy layer-consistency check with `certificate_verified=false`. Numerical callback evaluation remains uncertified. Generic numerical DD enclosure, population coverage, global Grassmann optimality, independent-host reproduction and new raw-data campaigns are not established by this preparation.

Canonical witness selection, endpoint checks, counters, bounds and interruption statuses retain version-specific contracts. An interrupted search without an incumbent is not a proof of infeasibility. Time limits are cooperative and cannot pre-empt a callback already running. Exact supplied-operand aggregation is separate from validating a scientific or monetary model.

## Verification and release engineering

1. Preserve the historical tags, archives, reports, failed attempts and their identifiers.
2. Perform the explicitly authorised tests and fresh builds on the exact candidate source. Never rename rc2 binaries to rc3.
3. Compare source package bytes with wheel and sdist, verify RECORD, reject unsafe or duplicate archive paths and rebuild the source archive after extraction.
4. Integrate the reviewed source into `main`, verify the actual commit/tree, then create the new tag and release. Build and publication evidence remain external and must identify those exact bytes.

Automatic CI triggers are absent from this candidate. Its workflow is manual-only and requires an explicit authorisation input. The repository owner must disable Actions **before the first remote write or pull request**, because the earlier remote workflow can trigger independently of the candidate file. No workflow has been started by preparing this source.

The historical mutation runner is blocked. A nonzero pytest return code alone cannot establish a killed mutant. See [docs/MUTATION_REVIEW_PROTOCOL.md](docs/MUTATION_REVIEW_PROTOCOL.md).

## History and limits

Exact rc2 identity and engineering files are preserved under `release/history/rc2_profile/`. Earlier rc1/P7 copies remain under `release/history/rc1_p7/`. P10-SD34, P10-SD37 and P10-SD40 describe their original historical source and software-only qualification scopes. The distinct historical D2 and Component C records do not transfer a complete PASS to this source. No finite suite proves universal correctness.

Programme REWORK, H-02 FAIL, H-14 FAIL, scientific Q12 and the recorded scientific limitations retain their historical identities. This software preparation does not grant a global PASS, resolve G0 BLOCKED or lift HOLD. An editorially prepared manuscript is not a new scientific execution.

## Licensing and attribution

Apache-2.0 applies to the included software surface defined by `LICENSING.md`, with individual exceptions retained. Manuscript, figure, evidence, private-provenance, third-party data and third-party content rights remain separate. Operational publication authority is deliberately not encoded in this software tree. `LICENSE` and `NOTICE` are included in distributions.

AI assistance in source review and preparation is described in [docs/AI_ASSISTANCE.md](docs/AI_ASSISTANCE.md). Tool assistance is not an independent authority or formal verification. Security reports should follow `SECURITY.md`; ordinary defects should follow `CONTRIBUTING.md`.
