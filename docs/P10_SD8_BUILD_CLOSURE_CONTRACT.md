# P10-SD8 build-closure contract

Version: `0.1.0.dev6`. Author: Antonio Clim. Private local candidate, not a public release.

## Recorded deterministic build recipe

The build-system requirement is exactly `setuptools==82.0.1` (setuptools 82.0.1) with backend `setuptools.build_meta`. The recorded build uses `SOURCE_DATE_EPOCH=1789430400`. `scripts/build_distributions.py` validates both values before building and refuses a conflicting backend or epoch. `build-recipe.json` and `build-system.lock.txt` provide a machine-readable local binding.

The captured setuptools wheel has SHA-256 `5b09495678e3abe774a2e7fdf407e284c35f5abff6f598119f248b589ed130c2`. It is a deterministic same-host repack retained from P10-SD7, **not an upstream-authenticated artefact**. The successful local rebuild is **not an independent-machine reproduction**, an upstream registry resolution or a portable multi-platform lock.

## Authority boundary

This contract closes F35 in the qualified local build-envelope scope only. It does not change any algorithm, theorem, empirical result, economic provenance claim, licence gate or publication authority. Upstream-authenticated dependency artefacts, immutable CI action SHAs, a digest-pinned container base, Python 3.11/3.12 execution and second-machine reproduction remain open.
