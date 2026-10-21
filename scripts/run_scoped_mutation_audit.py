#!/usr/bin/env python3
"""Blocked historical mutation entry point; no automatic kill classification.

The exact old helper is preserved under release/history/rc2_profile/scripts/.
A nonzero pytest return code alone is not evidence that a mutant was killed.
"""
from __future__ import annotations
import json


def main() -> int:
    print(json.dumps({"status":"UNRUN_REQUIRES_SEPARATE_MUTATION_PROTOCOL", "automatic_kill_classification":False, "historical_helper":"release/history/rc2_profile/scripts/run_scoped_mutation_audit.py", "protocol":"docs/MUTATION_REVIEW_PROTOCOL.md", "reason":"A passing baseline, protocol-bound mutants and independent causal classification are required. This command runs no project code and creates no output files."}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
