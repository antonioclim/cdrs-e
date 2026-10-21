# Mutation review boundary

The exact rc2 runner is retained under `release/history/rc2_profile/scripts/run_scoped_mutation_audit.py`. Its nonzero-return-code classification is not an accepted current mutation protocol. The active entry point fails closed and performs no project execution.

Any later campaign requires its own predeclared mutant identities, unchanged acceptance threshold and baseline groups, test-selection map, timeout/resource policy and independent causal classification. First establish a passing unmutated baseline for each relevant group. Distinguish collection/import/usage errors, timeouts, invalid mutations, unrelated failures, surviving mutants and validated kills. A return code of 1 is only a candidate test failure, not sufficient evidence of a kill; codes 2–5 or process/timeout failures must not count as kills. Classify causality from retained output and an appropriate unmutated control. Keep unresolved cases unresolved.

Historical D2/Q33 classifications remain version-bound and unchanged. This source preparation runs no mutation campaign and reports no new mutation score.
