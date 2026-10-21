# Reviewer quick start — local CDRS-E 0.1.0rc2 candidate

This local `0.1.0rc2` source candidate preserves the phase06 runtime sources and K1 repair. Status remains `LOCAL_SOFTWARE_CANDIDATE_RC2`; its metadata profile is `PREPUBLICATION_PROFILE_PENDING_IMPACT_CHECKS`. The active binding in `release/QUALIFICATION_STATE.json` identifies predecessor D2 qualification: 36 inherited criteria and a new complete Q33 PASS campaign, with the M12 acceptance-method extension designed after phase05. NOT_EXECUTED fields describe this changed profile at source-snapshot creation. There is no adopted public release or new archival DOI.

## Five-minute demonstration

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/reviewer_quick_start.py --run-claim-tests --output reviewer_quick_start_results.json
```

Acceptance target after separately authorised execution: `PASS`. No execution of this changed profile is reported here; predecessor D2 evidence is identified separately. The demonstration checks exact stored-input backend agreement, canonical tie resolution, callback non-certification and rejection of an invalid forest input. It does **not** reproduce historical VAR fits, bootstrap producers, population DD theorems, raw-data-to-result execution or generic DD enclosures.

## Full local verification

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/run_reviewer_pipeline.py --output-dir reviewer_pipeline_results
```

The pipeline runs six isolated test shards, the quick start and branch coverage.
