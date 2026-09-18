# CDRS-E 0.1.0rc1 — software-only release notes

- Apache-2.0 applies to the included software surface.
- Manuscript, supplementary, figure, evidence, private-provenance and generated-report paths are excluded from the repository and release assets.
- Twenty-eight registered scientific-payload files are byte-identical to the qualified SD37 candidate and, through SD37, to the SD35 scientific payload. `src/cdrse/__init__.py` differs only in its authorised module docstring; every subsequent byte and the AST after removing that docstring are identical.
- P10-SD34 remains authoritative for fresh rc1 scientific qualification. QUICK passed. FULL is `PASS_WITH_ORCHESTRATION_QUALIFICATION`: the interrupted parent attempt is retained and 28/28 independently completed shards were reconciled.
- P10-SD39 established the canonical repository identity and publication-durable metadata but was not promoted. P10-SD40 applies the bounded public-identity correction and performs the complete local source, packaging and installed-wheel re-freeze.
- The source ZIP, wheel and sdist are deterministically reconstructed twice, checked for zero deferred paths and subjected to complete source and installed-wheel testing.
- This source snapshot embeds no DOI. Archival identifiers, if later minted, must be real and are not retroactively fabricated in the frozen tag.
