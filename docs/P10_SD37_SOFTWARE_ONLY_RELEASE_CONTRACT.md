# P10-SD37 software-only release contract

## Scope

P10-SD37 derives a new local candidate from the immutable SD35 candidate. Every path rooted at `paper/`, `evidence/`, `provenance/` or `reports/` is excluded from the repository tree, source-and-tests ZIP, wheel and sdist. Excluded bytes remain only in the private audit wrapper and retain `CONTENT_LICENCE=DEFER` or source-specific terms.

## Scientific identity

The 29-file algorithmic payload listed in `release/ALGORITHMIC_PAYLOAD_IDENTITY.json` must be byte-identical to SD35. QUICK, FULL, DS1 and solver campaigns are not rerun solely for packaging remediation. P10-SD34 remains authoritative for those finite execution records.

## Packaging identity

The exact setuptools 84.0.0 build lineage remains recorded. P10-SD37 does not claim to have re-executed that backend. It deterministically reassembles the qualified wheel and sdist with the sanitised source tree, recomputes metadata and wheel `RECORD`, builds every asset twice and requires byte identity. The resulting wheel must pass installation and the full test suite.

## Authority

This contract authorises no remote object or operation. Repository creation or modification, push, pull request, merge, tag, release, GitHub Actions, PyPI, Zenodo, DOI, e-mail, editorial upload, submission and costs remain prohibited absent a later exact authorisation.
