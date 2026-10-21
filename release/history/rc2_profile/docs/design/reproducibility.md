# Reproducibility

The package records deterministic seeds, canonical input hashes, algorithm counters, backend identity, tolerances and termination reasons. The canonical source-build contract pins `setuptools 84.0.0`, `pip 26.2.1` and `SOURCE_DATE_EPOCH=1789689600`.

P10-SD34 is authoritative for the fresh rc1 source and installed tests, QUICK/FULL reconciliation, DS1, solver, CLI, formal and coverage evidence. The initial parent FULL orchestration remains recorded as interrupted; 28/28 independently completed shards were reconciled. No finite suite establishes universal correctness.

P10-SD37 removed deferred-content paths and qualified deterministic reassembly from the SD35 assets. P10-SD39 prepared publication-facing metadata and release-test repairs but stopped fail-closed before distribution construction. P10-SD40 changes only the module docstring in `src/cdrse/__init__.py`, preserves the other 28 registered files byte-identically and proves AST identity after removing the docstring. Because the exact setuptools 84.0.0 wheel was not re-acquired in the isolated transition environment, P10-SD40 deterministically reassembles the wheel and sdist from the qualified SD37 assets, rebuilds each asset twice, installs the resulting wheel and reruns the complete test suite. This is not an independent-machine or multi-platform reproduction.

Apache-2.0 applies to the software-only surface. Canonical repository metadata is embedded. No DOI is fabricated or embedded in this source snapshot.
