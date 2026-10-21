from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_rc2_exact_historical_copies_are_preserved() -> None:
    record = json.loads((ROOT / "release/history/rc1_p7/HISTORY_MANIFEST_SHA256.json").read_text())
    for row in record["files"]:
        payload = (ROOT / row["path"]).read_bytes()
        assert len(payload) == row["bytes"]
        assert hashlib.sha256(payload).hexdigest() == row["sha256"]

def test_rc2_new_state_does_not_inherit_historical_pass() -> None:
    q = json.loads((ROOT / "release/QUALIFICATION_STATE.json").read_text())
    assert q["candidate_status"] == "LOCAL_SOFTWARE_CANDIDATE_RC2"
    for key in ("build", "source_tests", "installed_runtime", "installed_tests", "coverage", "scoped_mutation_audit", "scientific_replay"):
        assert q[key] == "NOT_EXECUTED"
    assert q["global_scientific_PASS_claimed"] is False
    assert q["integrated_qualification"] == "PENDING_PUBLIC_PROFILE_IMPACT_CHECKS"
    assert q["state_is_source_snapshot_not_live_execution_registry"] is True
    b = q["active_qualification_binding"]
    assert b["predecessor_archive_sha256"] == "90198779ffd28c27c5e7b94589f6182a93229ae22425e582ef961a284cdba6f8"
    assert b["predecessor_source_manifest_sha256"] == "61bef2212b4c2b16e292c24224963c2b01cad33cd6bd1ea17bb92dec66550880"
    assert b["predecessor_complete_source_files"] == 175
    assert b["administrative_closure_sha256"] == "6ee4a21869e9ad5eb7ece70a4f4f70d1ffb63a20760f8a14653cee77a3c1e1c9"
    assert b["predecessor_qualification_status"] == "SCOPED_SUCCESSOR_QUALIFICATION_PASS_WITH_INHERITED_EVIDENCE"
    assert b["inherited_criteria"] == 36 and b["inherited_main_invocations"] == 37
    assert b["new_Q33"] == {"status": "PASS", "baseline_groups": 9, "baseline_cases": 34, "mutants": 12, "valid_classifications": 12, "killed": 12, "score": 1.0, "threshold": 0.7, "minimum_kills": 9, "hybrid_score": False}
    assert b["M12_method_extension_designed_after_observing_phase05"] is True
    assert b["current_profile_acceptance"] == "PENDING_SEPARATE_BOUNDED_OFFLINE_IMPACT_CHECKS"

def test_rc2_historical_envelope_reassembly_is_blocked() -> None:
    text = (ROOT / "scripts/reassemble_qualified_assets.py").read_text()
    assert "DEPENDENCY_BLOCKED" in text
    assert "fresh exact-backend build" in text
    recipe = json.loads((ROOT / "build-recipe.json").read_text())
    assert recipe["old_qualified_assets_permitted_as_build_inputs"] is False
