# Reviewer quick start — local APEX Phase-7 candidate

This is a **local create-only review candidate** built from public CDRS-E 0.1.0rc1. It is not a GitHub release, Zenodo version or public successor.

## Five-minute demonstration

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/reviewer_quick_start.py --run-claim-tests --output reviewer_quick_start_results.json
```

Expected status: `PASS`. The demonstration checks exact stored-input backend agreement, canonical tie resolution, callback non-certification and rejection of an invalid forest input. It does **not** reproduce historical VAR fits, bootstrap producers, population DD theorems, raw-data-to-result execution or generic DD enclosures.

## Full local verification

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/run_reviewer_pipeline.py --output-dir reviewer_pipeline_results
```

The pipeline runs six isolated test shards, the quick start and branch coverage.
