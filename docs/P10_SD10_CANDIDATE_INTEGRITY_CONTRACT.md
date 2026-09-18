# P10-SD10 candidate-integrity contract

## Status

`cdrs-e 0.1.0.dev7` is a **source-only, unpromoted candidate**. The last qualified software identity remains `0.1.0.dev6`.

## Corrected inconsistencies

The supplied SD9 candidate produced 10/12 passes in its own upstream-provenance test and 11/18 passes across the SD8/SD9 targeted checks. Its `pyproject.toml` requested setuptools 84.0.0 while `build-recipe.json`, the build script, the SD8 contract and parts of the release ledger still described the dev6 setuptools 82.0.1 envelope. The candidate also stated that official metadata hashes were bound while its metadata files were empty placeholders.

This corrected tree:

- retains the qualified dev6 build envelope as a historical record;
- binds selected fields from the official PyPI release metadata for setuptools 84.0.0 and pip 26.2.1;
- records the verified signed Git tag objects and target commits;
- makes the dev7 source recipe, lock, build script, metadata and release gates internally consistent;
- keeps the absence of upstream artefact bytes, dev7 distributions, runtime and independent execution explicit.

## Authority boundary

Passing source tests establishes consistency of this source candidate in the observed host environment. It does not authenticate missing upstream bytes, qualify a dev7 wheel or sdist, reproduce the project on a second machine, close F03/F15, validate all scientific claims or authorise publication.
