from __future__ import annotations
import json
from pathlib import Path
import tomllib
ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "https://github.com/antonioclim/cdrs-e"
VOLATILE_KEYS = {"public_release_authorized", "public_release_authorised", "remote_actions_performed", "remote_actions_authorised", "tag_authorized", "github_release_authorized", "github_publication_authorized", "github_actions_authorized", "zenodo_deposit_authorized", "doi_reservation_authorized", "pypi_upload_authorized", "submission_authorized"}
def _json(path: str) -> dict: return json.loads((ROOT / path).read_text(encoding="utf-8"))
def test_sd9_01_public_surface_is_fail_closed() -> None:
    p = _json("release/PUBLIC_SURFACE_SCOPE.json"); assert p["default_rule"] == "FAIL_CLOSED" and p["scope"] == "SOFTWARE_ONLY" and p["operational_authority_embedded"] is False
def test_sd9_02_forbidden_top_level_segments_are_absent() -> None: assert not any((ROOT / x).exists() for x in ("paper", "evidence", "provenance", "reports"))
def test_sd9_03_repository_identity_is_consistent() -> None:
    py = tomllib.loads((ROOT / "pyproject.toml").read_text()); assert py["project"]["urls"]["Repository"] == REPOSITORY and _json("codemeta.json")["codeRepository"] == REPOSITORY and _json("release/PUBLICATION_IDENTITY.json")["canonical_repository_url"] == REPOSITORY
def test_sd9_04_private_remote_plans_are_not_publicly_distributed() -> None:
    assert not any((ROOT / p).exists() for p in ("release/GITHUB_PUBLIC_REPOSITORY_PLAN.json", "release/ZENODO_DEPOSIT_PLAN.json", "release/REMOTE_AUTHORITY_BOUNDARY.md", "release/zenodo-metadata-DRAFT.json"))
def test_sd9_05_release_notes_are_publication_accurate() -> None:
    t = (ROOT / "release/RELEASE_NOTES_v0.1.0rc1.md").read_text(); assert "canonical repository identity" in t and "embeds no DOI" in t and "unauthorised" not in t.lower()
def test_sd9_06_archival_policy_prohibits_fabrication() -> None:
    t = (ROOT / "release/ARCHIVAL_METADATA_POLICY.md").read_text(); assert "no fabricated DOI" in t and "frozen release-candidate tag must not be rewritten" in t
def test_sd9_07_publication_contract_separates_artifact_and_operation_state() -> None:
    t = (ROOT / "docs/P10_SD40_BOUNDED_PUBLIC_IDENTITY_CORRECTION_CONTRACT.md").read_text(); assert "contains no conversational or account-level authorisation flags" in t and "performed outside the artefact" in t
def test_sd9_08_source_archive_builder_uses_durable_identity() -> None:
    t = (ROOT / "scripts/build_source_archive.py").read_text(); assert "P10SD40_PUBLICATION_DURABLE" in t and "Operational publication authority is deliberately external" in t
def test_sd9_09_ci_is_verification_only() -> None:
    t = (ROOT / ".github/workflows/ci.yml").read_text(); assert "contents: read" in t and "contains no publication or deployment step" in t and "twine upload" not in t and "zenodo" not in t.lower()
def test_sd9_10_algorithmic_identity_registry_is_closed() -> None:
    r = _json("release/ALGORITHMIC_PAYLOAD_IDENTITY.json"); assert r["comparison"] == "SD37_TO_SD40" and r["file_count"] == 29 and r["byte_identical_count"] == 28 and r["docstring_only_correction_count"] == 1 and r["all_identical"] is False
def test_sd9_11_private_provenance_is_represented_only_by_bounded_public_records() -> None:
    assert not (ROOT / "provenance").exists(); assert (ROOT / "release/TOOLCHAIN_LOCK.json").exists() and (ROOT / "release/BUILD_DERIVATION.json").exists()
def test_sd9_12_current_public_json_has_no_volatile_authority_keys() -> None:
    for path in ("release-gates.json", "build-recipe.json", "release/PUBLIC_SURFACE_SCOPE.json", "release/PUBLICATION_IDENTITY.json"): assert VOLATILE_KEYS.isdisjoint(_json(path))
