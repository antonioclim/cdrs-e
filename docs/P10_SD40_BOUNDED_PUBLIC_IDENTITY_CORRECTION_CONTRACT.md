# P10-SD40 bounded public-identity correction and publication-durability contract

## Durable public identity

- software: `cdrs-e`;
- version: `0.1.0rc1`;
- canonical repository: `https://github.com/antonioclim/cdrs-e`;
- release-candidate tag: `v0.1.0rc1`;
- software licence: Apache-2.0;
- public surface: software only.

The public source tree contains no conversational or account-level authorisation flags. Repository upload, release publication, archival deposition and DOI registration are operations performed outside the artefact. Their occurrence does not change the truth of the repository metadata.

## Bounded identity correction

P10-SD40 changes exactly the first line of `src/cdrse/__init__.py`, replacing the private-candidate module docstring with `CDRS-E auditable research software release candidate.` No other byte in that file changes. Twenty-eight other files registered in `release/ALGORITHMIC_PAYLOAD_IDENTITY.json` remain byte-identical to SD37. The AST of `src/cdrse/__init__.py`, after removing its module docstring, is identical to the SD37 AST. The result is reported as `28/28 byte-identical + 1 docstring-only publication-identity correction`, never as 29/29 byte-identical.

## Scientific and evidential boundary

P10-SD34 remains authoritative for fresh rc1 scientific execution evidence. P10-SD40 reruns the complete source and installed-wheel suites but does not rerun QUICK, FULL, DS1 or a mutation campaign. The bounded docstring correction changes no executable statement and no algorithmic AST.

No finite test catalogue establishes universal correctness. TS0 remains not met, F03 and F15 remain open and programme completion remains false.

## DOI policy

No DOI is fabricated or embedded in this source snapshot. A DOI may be added only after a real archival record exists and should normally be introduced in external release metadata or a subsequent source revision rather than by rewriting the frozen tag.
