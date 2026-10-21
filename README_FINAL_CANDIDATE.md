# CDRS-E 0.1.0 — research software release

Author and maintainer: Antonio Clim. Contact: Antonio.clim@csie.ase.ro. ORCID: https://orcid.org/0000-0003-4745-0431.
Canonical repository: https://github.com/antonioclim/cdrs-e.

## Source identity and current assurance

This source prepares normal version `0.1.0`, with status `PREPARED_RELEASE_010` and release channel `release`. Its build, tests, installation, coverage, mutation assessment and runtime checks are **UNRUN** for these bytes. Source review and syntactic checks do not establish execution or universal correctness.

The immediate parent is the reviewed `0.1.0rc3` source snapshot at commit `6a9f2d43c62d45e78ec619ef2be582e4915ef50f`, tree `d742e6316887e1ea2cc4aafcd8e46ca5ca7a0dd0`. That prepared snapshot was not a published rc3 release. Version 0.1.0 retains its runtime-contract and release-engineering corrections; the promotion synchronises version metadata without claiming a new algorithmic execution.

The public predecessor remains `v0.1.0rc2`, commit `c4bedf30c3b5967ade38b0aeac897529a67a7672`, software DOI https://doi.org/10.5281/zenodo.23409442. Historical rc1 retains https://doi.org/10.5281/zenodo.22841999. The `v0.1.0` tag must identify the exact reviewed 0.1.0 commit integrated into `main`. No new commit, publication date or version DOI is guessed in this snapshot; actual publication and any later execution are recorded externally with their exact identities.

The associated manuscript is *Which Channels Should We Keep? Uniform Bounds for Cut-Based Selection in Gaussian Vector Autoregressions*. Its editorial R1.4 identity is separate from this software source and is a derivative of the verified v15 corpus, not historical V5.1. The source does not include manuscript files, article figures, private wrappers or raw third-party datasets.

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
2. Record any explicitly authorised execution on the exact source separately from publication. Tests, fresh builds and installed-form checks remain UNRUN for 0.1.0; no wheel or sdist is supplied by this preparation. Never relabel historical binaries as 0.1.0.
3. Future distribution qualification must compare source package bytes with wheel and sdist, verify RECORD, reject unsafe or duplicate archive paths and rebuild the source archive after extraction.
4. Integrate the reviewed 0.1.0 source into `main`, verify the actual commit/tree, then create the normal `v0.1.0` release without the pre-release flag. Source packaging and publication do not establish an executed build or test result. Publication identity remains external and must identify those exact bytes. See [docs/NORMAL_RELEASE_0_1_0.md](docs/NORMAL_RELEASE_0_1_0.md).

The retained validation workflow is manual-only, requires separate execution authorisation and is not required to create the normal source release. Actions remains disabled during manual source integration and publication. This preparation starts no workflow and uses no Cloud environment.

The historical mutation runner is blocked. A nonzero pytest return code alone cannot establish a killed mutant. See [docs/MUTATION_REVIEW_PROTOCOL.md](docs/MUTATION_REVIEW_PROTOCOL.md).

## History and limits

Exact rc2 identity and engineering files are preserved under `release/history/rc2_profile/`. Earlier rc1/P7 copies remain under `release/history/rc1_p7/`. P10-SD34, P10-SD37 and P10-SD40 describe their original historical source and software-only qualification scopes. The distinct historical D2 and Component C records do not transfer a complete PASS to this source. No finite suite proves universal correctness.

Programme REWORK, H-02 FAIL, H-14 FAIL, scientific Q12 and the recorded scientific limitations retain their historical identities. This software preparation does not grant a global PASS, resolve G0 BLOCKED or lift HOLD. An editorially prepared manuscript is not a new scientific execution.

## Licensing and attribution

Apache-2.0 applies to the included software surface defined by `LICENSING.md`, with individual exceptions retained. Manuscript, figure, evidence, private-provenance, third-party data and third-party content rights remain separate. Operational publication authority is deliberately not encoded in this software tree. `LICENSE` and `NOTICE` are included in distributions.

AI assistance in source review and preparation is described in [docs/AI_ASSISTANCE.md](docs/AI_ASSISTANCE.md). Tool assistance is not an independent authority or formal verification. Security reports should follow `SECURITY.md`; ordinary defects should follow `CONTRIBUTING.md`.
