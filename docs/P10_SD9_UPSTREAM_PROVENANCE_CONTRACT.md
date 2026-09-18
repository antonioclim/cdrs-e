# P10-SD9/SD10 upstream-provenance contract

This tree is a **corrected, unpromoted source candidate** for `cdrs-e 0.1.0.dev7`. The originally supplied SD9 candidate contained placeholder PyPI metadata files and contradictory build-closure records. P10-SD10 preserves those failures in its external audit package and repairs the source candidate without constructing or qualifying a dev7 distribution.

The current source binds the official PyPI release-file metadata for `setuptools==84.0.0` and `pip==26.2.1`, including filenames, sizes and SHA-256 values. It also records signed Git tag objects and their target commits. These are metadata bindings only: the corresponding upstream wheel and sdist bytes were not acquired or hashed locally in this environment.

GitHub Actions are pinned by commit SHA. The Docker base-image digest, upstream artefact acquisition, dev7 wheel/sdist/runtime construction, QUICK/FULL replay and genuinely independent second-machine execution remain open. No release, licence, repository write, deposition or submission is authorised.
