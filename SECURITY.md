# Security and scientific-integrity reporting

Supported release line: `0.1.0rc1`.

Report suspected vulnerabilities privately to `Antonio.clim@csie.ase.ro` with the subject `CDRS-E security report`. Include the affected version, a minimal reproduction, impact and any proposed mitigation. Do not include secrets, personal data or embargoed third-party material. When private vulnerability reporting is enabled for the canonical repository, its Security tab may also be used: `https://github.com/antonioclim/cdrs-e/security/policy`.

Ordinary defects may be reported through `https://github.com/antonioclim/cdrs-e/issues`. Security issues include arbitrary-file writes, unsafe archive extraction, dependency confusion and unbounded resource consumption. Scientific-integrity issues include invalid bounds, vacuous certificates, hidden failed runs and promotion of numerical evidence to exact claims.

The finite source-boundary and AST checks are not taint analysis, a native-extension audit or an exhaustive transitive vulnerability assessment. No response-time or remediation-time guarantee is made.
