# Finite validation plan for CDRS-E 0.1.0 — UNRUN

The `RC3_VALIDATION_PLAN.md` filename, `run_rc3_release_validation.py` entry point, regression filenames and `CDRSE_RC3_*` schema identifiers are retained compatibility names. The current software version is `0.1.0`; these names do not make it a release candidate.

Preparing or reading these instructions does not authorise execution. The exact source hash, environment, commands, resource limits, output locations and stop policy must be adopted separately. A normal source release does not claim these checks have executed. Preserve every failed or partial attempt. Do not run scientific replay, raw-data fitting, new simulations, new fixtures from scientific payloads or a mutation campaign under this plan.

## Source and finite regression checks

From a fresh, version-verified working copy with dependencies available:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m coverage run --branch -m pytest -q -p no:cacheprovider tests
python -m coverage report --fail-under=85
```

These checks execute project code, including scientific arithmetic in finite unit/regression tests. They require explicit authorisation; they are not administrative metadata reads. Record actual collected cases, failures, skips and coverage, rather than inheriting an earlier case count.

## Fresh administrative builds and distribution checks

Use the exact declared backend. Build in two separate fresh source copies. The builder refuses existing build/dist/egg-info destinations and does not clean up earlier attempts:

```text
python scripts/build_distributions.py
python scripts/build_source_archive.py
python scripts/verify_distribution.py
```

Compare the two wheels, sdists and curated source ZIPs byte for byte in the recorded environment. Verify source-to-package byte binding and wheel RECORD. Extract the curated source ZIP into a new directory, reconstruct it at a separate new destination and compare the complete member inventory and bytes. The two generated SOURCE_* members are not source inputs. All these outcomes remain UNRUN.

## Installed forms and current identity

Install wheel and sdist separately into new environments using an explicit dependency policy. Verify actual import provenance, version, schema resources and the declared finite installed checks. Rebuild a wheel from the sdist and compare it under the same recorded recipe. Run source-bound identity checks before producing artefacts, or in a separate pristine copy, because the identity suite forbids committed distribution envelopes under dist/.

The retained workflow is manual-only and is optional for the normal source release. Before the first remote write or PR, the owner must disable the earlier repository Actions workflow or separately authorise its execution. Re-enabling and dispatching validation requires a distinct decision. The authorisation input is `AUTHORISE_CDRSE_010_VALIDATION`; supplying it is an execution action, not a document check.

## Receipt boundary

Do not insert a guessed commit, release date or DOI into source. After reviewed integration into main, verify the actual commit/tree and tag. A later receipt must bind that source and its exact uploaded assets. No global scientific PASS, G0 unblocking, HOLD release or submission approval follows automatically from software checks.

## CI artefact collection

Only the Python 3.12 job is the candidate authoritative build for a later release. Python 3.11 and 3.13 outputs are diagnostic matrix products; do not assume byte identity across interpreters. After all required steps succeed, the job creates ARTIFACT_MANIFEST.json and SHA256SUMS.txt with the exact observed job commit and file hashes. It does not infer that this commit has been integrated into main. Later integration must compare the reviewed source tree with the actual main/tag identity.

The workflow attempts to preserve available files, including partial evidence, as `cdrse-0.1.0-<Python version>-<job commit>`. An early failure may produce no downloadable artifact. Failed or partial output is not qualified for release. Before dispatch, verify the official `actions/upload-artifact@v4` reference and other third-party action references; this phase has not resolved that tag to a newly checked immutable commit.

The workflow builds from a separate fresh `git archive` copy of the exact job commit. This avoids overwriting or reusing build/egg-info material created by the earlier editable installation and tests. Its artefact paths therefore lie under the runner's temporary build directory, with QA outputs in a separate temporary directory. The downloaded artifact may preserve directory structure; select release candidates by ARTIFACT_MANIFEST.json and SHA256SUMS.txt, not by an assumed flattened ZIP layout. The authoritative Python 3.12 job now calls `scripts/run_rc3_release_validation.py`, which encodes the repeated-build, source-ZIP roundtrip, sdist-to-wheel and declared installed-form routes described below. These are prepared commands, not executed evidence.

## One authorised GUI dispatch: complete finite route

The Python 3.12 job runs `python scripts/run_rc3_release_validation.py --commit "$GITHUB_SHA" --qa-dir "$QA_DIR"` after its initial fresh build and source tests. The driver imports no project modules itself, but its future commands deliberately execute separately authorised finite tests and builds. It permits at most 24 subprocess commands. A selector loop checks a 1,200-second cumulative deadline and a per-command deadline of at most 300 seconds, capped by remaining wall time. Each child starts a separate POSIX session; timeout or the first observed output excess requests SIGKILL for that process group, then permits at most five seconds for pipe drain and direct-child reap. Each Python capture buffer retains at most 8 MiB per stream, including during cleanup. The receipt records observed and retained bytes, truncation and incomplete cleanup. These are prepared controls, not executed evidence. Descendants that escape the process group are not contained; OS calls, report I/O, hard cancellation, OOM and runner termination are not forcibly preempted by this loop. Keep the independent outer job timeout of 30 minutes. Kernel/tool buffers, memory and internal tool temporary materialisation are not measured or certified by these source controls. A hard stop may prevent the final receipt or artifact upload; missing or partial evidence is unverified and not release eligible.

The finite AST security scanner retains its general subprocess.Popen prohibition. It reports one transparent exception bound to the exact SHA-256 of this administrative driver; any driver byte change invalidates that exception and requires a new review. This exception is neither scientific authorisation nor a security/containment proof.

The encoded steps are:

1. Record the actual host `pip freeze --all`, then safely verify/extract the curated source manifest into two new directories.
2. Build source ZIP, wheel and sdist independently in both copies using the pinned backend and SOURCE_DATE_EPOCH. Compare all three against each other and against the initial candidate assets.
3. Safely extract the curated source ZIP into another new directory, rebuild it and require identical complete ZIP bytes.
4. Rebuild the wheel from the sdist with `pip wheel --no-index --no-deps --no-build-isolation` and require identical wheel bytes.
5. Create separate wheel and sdist virtual environments with `--system-site-packages`, install the candidate with `--ignore-installed --no-index --no-deps --no-build-isolation` and record that host dependencies are reused. This is neither hermetic dependency resolution nor an independent-host reproduction.
6. Copy the following literal finite tests outside the checkout: `tests/unit/test_hashing_models.py`, `test_objectives_backends.py`, `test_economics_certificates.py`, `test_schemas_protocols.py`, `tests/claims/test_executable_claims.py` and `tests/regression/test_rc3_runtime_boundaries.py`. Copy the two declared example JSON inputs and original conftest; its `src` target is deliberately nonexistent. Append an administrative provenance guard without changing scientific assertions.
7. Run the installed subset with isolated Python, no PYTHONPATH, user-site or external pytest plugins. Require every loaded cdrse module in the test process to resolve under that child virtual environment's site-packages. Retain before/after and in-process provenance, actual JUnit cases and child pip-freeze output. This is a declared finite subset, not a full installed suite. No failures, errors or skips are accepted.
8. Require the candidate assets to remain unchanged. Only a complete successful route records `SCOPED_RELEASE_VALIDATION_PASS`. Any command, timeout, structural, provenance or byte mismatch records ERROR and stops; partial logs and directories remain.

This is not a fresh full D2 qualification, Q33 mutation campaign, independent-host reproduction, raw-data campaign or scientific replay. Historical failures, G0 BLOCKED, HOLD and global PASS false are unchanged. The source-state records remain UNRUN; a later external job receipt binds the actual execution to its exact commit and assets.

The authoritative ARTIFACT_MANIFEST.json is written only after a matching successful RELEASE_VALIDATION.json binds those same final assets. Diagnostic Python 3.11 and 3.13 jobs do not claim this complete route. Available nested command logs, JUnit, provenance and freeze outputs are uploaded even after a failure; a failed artifact is not eligible for release.
