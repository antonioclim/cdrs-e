from __future__ import annotations
import json
from pathlib import Path
import tomllib
ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "https://github.com/antonioclim/cdrs-e"
SETUPTOOLS_SHA = "51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
SETUPTOOLS_SDIST_SHA = "f4695c21257f0d9b537ec2692c941d02ee143b7cc1276941349a546573b2ef73"
PIP_SHA = "71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e"
PIP_SDIST_SHA = "f6ad667e89a1fe78046c8f13232b247200f5258d7828f3f7883d660878e0813f"
def _json(path: str) -> dict: return json.loads((ROOT / path).read_text(encoding="utf-8"))
def test_sd10_01_version_surfaces_are_consistent() -> None:
    assert tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"] == "0.1.0rc1"; assert '__version__ = "0.1.0rc1"' in (ROOT / "src/cdrse/_version.py").read_text(); assert 'version: "0.1.0rc1"' in (ROOT / "CITATION.cff").read_text(); assert _json("codemeta.json")["version"] == "0.1.0rc1"
def test_sd10_02_release_gates_match_publication_identity() -> None:
    g = _json("release-gates.json"); assert g["software_version"] == "0.1.0rc1" and g["canonical_repository_url"] == REPOSITORY and g["artifact_state_model"] == "PUBLICATION_DURABLE"
def test_sd10_03_setuptools_record_binds_official_files() -> None:
    f = _json("release/TOOLCHAIN_LOCK.json")["files"]; assert f["setuptools-84.0.0-py3-none-any.whl"]["sha256"] == SETUPTOOLS_SHA and f["setuptools-84.0.0-py3-none-any.whl"]["size"] == 818216 and f["setuptools-84.0.0.tar.gz"]["sha256"] == SETUPTOOLS_SDIST_SHA
def test_sd10_04_pip_record_binds_official_files() -> None:
    f = _json("release/TOOLCHAIN_LOCK.json")["files"]; assert f["pip-26.2.1-py3-none-any.whl"]["sha256"] == PIP_SHA and f["pip-26.2.1-py3-none-any.whl"]["size"] == 1816632 and f["pip-26.2.1.tar.gz"]["sha256"] == PIP_SDIST_SHA
def test_sd10_05_setuptools_git_release_evidence_is_scoped() -> None:
    t = _json("release/TOOLCHAIN_LOCK.json")["git_release_evidence"]["setuptools"]; assert t["annotated_tag_object_sha"] == "cda52b336d048ebd773d28d2313859ec0ab258b5" and t["commit_sha"] == "72e919a8b10aaafc041205d4e3ae0e6a2e1e5f87"
def test_sd10_06_pip_git_release_evidence_is_scoped() -> None:
    t = _json("release/TOOLCHAIN_LOCK.json")["git_release_evidence"]["pip"]; assert t["annotated_tag_object_sha"] == "4a0f8bbcfc8057154d16a88632ea43389116d992" and t["commit_sha"] == "634a6ec1a5d9dcc2433571cdb2f4c58a4bb29caf"
def test_sd10_07_current_record_does_not_claim_reacquisition() -> None:
    p = _json("release/TOOLCHAIN_LOCK.json")["p10_sd40"]; assert p["exact_toolchain_bytes_reacquired"] is False and p["exact_backend_executed"] is False
def test_sd10_08_recipe_states_actual_derivation() -> None: assert _json("build-recipe.json")["current_derivation_method"] == "DETERMINISTIC_REASSEMBLY_FROM_QUALIFIED_SD37_ASSETS"
def test_sd10_09_ci_bootstrap_uses_hash_lock() -> None:
    text = (ROOT / ".github/workflows/ci.yml").read_text(); assert "build-system.lock.txt" in text and "--require-hashes" in text
def test_sd10_10_public_scope_is_fail_closed() -> None: assert _json("release/PUBLIC_SURFACE_SCOPE.json")["default_rule"] == "FAIL_CLOSED"
def test_sd10_11_current_contract_states_publication_durable_software_only() -> None:
    text = (ROOT / "docs/P10_SD40_BOUNDED_PUBLIC_IDENTITY_CORRECTION_CONTRACT.md").read_text().lower(); assert "publication-durability" in text and "software only" in text
def test_sd10_12_no_forbidden_top_level_directories_are_present() -> None: assert not any((ROOT / x).exists() for x in ("paper", "evidence", "provenance", "reports"))
def test_sd10_13_toolchain_record_covers_only_named_releases() -> None:
    assert set(_json("release/TOOLCHAIN_LOCK.json")["files"]) == {"setuptools-84.0.0-py3-none-any.whl", "setuptools-84.0.0.tar.gz", "pip-26.2.1-py3-none-any.whl", "pip-26.2.1.tar.gz"}
def test_sd10_14_result_schema_matches_source_candidate() -> None: assert "0.1.0rc1" in _json("src/cdrse/schema_files/result_contract.schema.json")["title"]
def test_sd10_15_readme_distinguishes_execution_packaging_and_transition_phases() -> None:
    text = (ROOT / "README.md").read_text(); assert "P10-SD34" in text and "P10-SD37" in text and "P10-SD40" in text and "software-only" in text
def test_sd10_16_public_repository_identity_is_durable() -> None:
    assert _json("codemeta.json")["codeRepository"] == REPOSITORY and _json("release/PUBLICATION_IDENTITY.json")["canonical_repository_url"] == REPOSITORY
def test_sd10_17_docker_and_second_machine_gates_remain_open() -> None:
    g = _json("release-gates.json")["reproducibility_limits"]; assert g["docker_digest_execution"] is False and g["independent_machine_execution"] is False
def test_sd10_18_candidate_contains_no_fabricated_doi() -> None:
    assert _json("release-gates.json")["source_snapshot_archival_identity"]["doi_embedded"] is False and "doi" not in _json("codemeta.json") and "doi:" not in (ROOT / "CITATION.cff").read_text().lower()
