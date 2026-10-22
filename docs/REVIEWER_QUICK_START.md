# CDRS-E 0.1.1 current publication record

CDRS-E 0.1.1 was published on 22 October 2026. Archival DOI: https://doi.org/10.5281/zenodo.23555624. GitHub release: https://github.com/antonioclim/cdrs-e/releases/tag/v0.1.1. The published source is fixed by commit `89d5325e65f55ed6ec58522b6537d904dd5acc44` and tree `b673f78db8099ef4b67ac20218846b03da8dabe8`. Finite QA2 validation on one Python 3.12.14 host reran 79 corrected-source cases and retained 16 earlier administrative checks with unchanged relevant identities. Final wheel/sdist and installed-wheel provenance checks passed within their declared scope. The full suite, Python 3.11/3.13 matrix, independent-host reproduction and new scientific campaigns were not run.

See [the published identity and documentary-update boundary](PUBLISHED_0_1_1_IDENTITY.md). No test or full reviewer pipeline is run by this documentation update.

## Historical preparation record retained verbatim

The following text is the frozen preparation record. Candidate and UNRUN wording below is historical; it does not undo publication or the separately recorded finite QA2 results.

# Reviewer quick start — prepared CDRS-E 0.1.1

Status: `PREPARED_RELEASE_011`; the full reviewer pipeline is UNRUN. Any bounded QA2 results are separately hash-bound. The public 0.1.0 predecessor and its separate historical D2 and Component C records do not establish a new execution of this source.

After separate execution authorisation and dependency preparation:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/reviewer_quick_start.py --run-claim-tests --output reviewer_quick_start_results.json
```

This finite demonstration checks retained exact stored-cut examples, canonical-witness agreement, callback non-certification and invalid-input rejection. It does not reproduce raw-data fitting, bootstrap generation, population DD results or generic DD numerical enclosures.

For the source suite and coverage, use the separately authorised commands in [RC3_VALIDATION_PLAN.md](RC3_VALIDATION_PLAN.md). The reviewer pipeline creates a new output directory and fails closed on test, timeout, coverage erase, combine, JSON or report failure. Historical counts and mutation scores are not a current acceptance criterion.
