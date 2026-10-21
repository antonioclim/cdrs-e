# Reviewer quick start — prepared CDRS-E 0.1.0rc3

Status: `PREPARED_CANDIDATE_RC3`; all rc3 execution is UNRUN. The public rc2 predecessor and its separate historical D2 and Component C records do not establish a new execution of this source.

After separate execution authorisation and dependency preparation:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/reviewer_quick_start.py --run-claim-tests --output reviewer_quick_start_results.json
```

This finite demonstration checks retained exact stored-cut examples, canonical-witness agreement, callback non-certification and invalid-input rejection. It does not reproduce raw-data fitting, bootstrap generation, population DD results or generic DD numerical enclosures.

For the source suite and coverage, use the separately authorised commands in [RC3_VALIDATION_PLAN.md](RC3_VALIDATION_PLAN.md). The reviewer pipeline creates a new output directory and fails closed on test, timeout, coverage erase, combine, JSON or report failure. Historical counts and mutation scores are not a current acceptance criterion.
