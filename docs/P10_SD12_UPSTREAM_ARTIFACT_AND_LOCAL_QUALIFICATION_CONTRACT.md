# P10-SD12 upstream-artifact and local dev7 qualification contract

## Status

`cdrs-e 0.1.0.dev7` is the local P10-SD12 qualification identity. The recorded build uses `setuptools 84.0.0`, `pip 26.2.1` and `SOURCE_DATE_EPOCH=1789430400`.

## Upstream artefact binding

The named pip wheel was obtained from the official `pypa/pip` 26.2.1 release workflow artefact. The named setuptools wheel was extracted from the official `pypa/virtualenv` 21.7.10 release workflow artefact, where it is embedded as a seed wheel. Both files were hashed locally and match the SHA-256 values in the official PyPI release metadata snapshots already bound by SD10.

This transport chain establishes byte identity for the two named wheel files. It is not a universal supply-chain attestation and it does not authenticate every transitive or native dependency.

## Local qualification scope

P10-SD12 may qualify source, wheel, sdist, a new immutable runtime and the declared QUICK/FULL replay on the observed CPython 3.13 Linux x86_64 host. Scientific dependencies may be reused from the same host where explicitly recorded. The exact build backend and epoch are fixed and the wheel rebuilt from the sdist must be compared byte-for-byte.

## Authority boundary

Local qualification is not independent-machine reproduction. No public release, PyPI upload, repository publication, Zenodo deposition, licence selection or journal submission is authorised. F03/F15, TS0, literature-priority claims and the author-decision categories remain separate gates.

## Deterministic sdist envelope

The first two SD12 builds produced identical wheel bytes and identical sdist member payloads but different sdist envelopes because build-time timestamps remained in the TAR/GZIP metadata. F41 preserves that failure and the final recipe normalises member order, ownership and timestamps after backend construction. The final sdist must be byte-identical across two clean builds, and a wheel rebuilt from it must match the qualified wheel byte-for-byte.
