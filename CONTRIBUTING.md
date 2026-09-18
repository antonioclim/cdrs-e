# Contributing to CDRS-E

CDRS-E is maintained by Antonio Clim. The canonical repository is `https://github.com/antonioclim/cdrs-e`.

Before proposing a change:

1. open an issue describing the defect, scientific boundary or documentation problem;
2. keep exact, numerical and statistical claims explicitly separated;
3. add deterministic tests for every behavioural change;
4. preserve seeds, input hashes and provenance relevant to the change;
5. avoid introducing manuscript, evidence, private-provenance or generated-report material into the software-only tree;
6. rebuild and verify the source archive, wheel and sdist;
7. pass the complete source and installed-wheel suites;
8. update the changelog and any affected contract.

Pull requests are maintainer-reviewed. A passing CI run is necessary but not sufficient for acceptance: scientific semantics, licensing scope and release metadata are reviewed separately. Security vulnerabilities must not be disclosed in a public issue; use the process in `SECURITY.md`.
