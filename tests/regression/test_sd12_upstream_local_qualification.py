from __future__ import annotations
import json
from pathlib import Path
import tomllib
ROOT = Path(__file__).resolve().parents[2]
SETUPTOOLS_SHA = "51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
PIP_SHA = "71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e"
def _json(path: str) -> dict: return json.loads((ROOT / path).read_text(encoding="utf-8"))
def test_sd12_01_exact_backend_pin() -> None: assert tomllib.loads((ROOT / "pyproject.toml").read_text())["build-system"]["requires"] == ["setuptools==84.0.0"]
def test_sd12_02_upstream_lineage_status() -> None: assert _json("build-recipe.json")["qualified_sd37_toolchain_lineage_locally_hash_verified"] is True
def test_sd12_03_setuptools_byte_identity_record() -> None: assert _json("release/TOOLCHAIN_LOCK.json")["files"]["setuptools-84.0.0-py3-none-any.whl"]["sha256"] == SETUPTOOLS_SHA
def test_sd12_04_pip_byte_identity_record() -> None: assert _json("release/TOOLCHAIN_LOCK.json")["files"]["pip-26.2.1-py3-none-any.whl"]["sha256"] == PIP_SHA
def test_sd12_05_transport_is_not_reinvented() -> None: assert _json("release/TOOLCHAIN_LOCK.json")["p10_sd40"]["no_new_upstream_authentication_claim"] is True
def test_sd12_06_build_recipe_identity() -> None:
    d = _json("build-recipe.json"); assert d["software_version"] == "0.1.0rc1" and d["candidate_status"] == "PUBLICATION_DURABLE_SOFTWARE_ONLY_RC1"
def test_sd12_07_recipe_separates_lineage_from_current_execution() -> None:
    d = _json("build-recipe.json"); assert d["qualified_sd37_toolchain_lineage_locally_hash_verified"] and not d["exact_backend_reacquired_or_executed_in_p10_sd40"]
def test_sd12_08_release_gates_record_current_quick_full() -> None:
    q = _json("release-gates.json")["qualification"]; assert q["quick_status"] == "PASS" and q["full_status"] == "PASS_WITH_ORCHESTRATION_QUALIFICATION" and q["full_parent_interruption_relabelled_as_pass"] is False
def test_sd12_09_operational_authority_is_external_to_public_metadata() -> None:
    g = _json("release-gates.json"); assert g["operational_authority_embedded"] is False and _json("release/PUBLIC_SURFACE_SCOPE.json")["operational_authority_embedded"] is False
def test_sd12_10_independent_machine_not_claimed() -> None:
    assert _json("release-gates.json")["reproducibility_limits"]["independent_machine_execution"] is False and _json("build-recipe.json")["independent_machine_reproduction"] is False
def test_sd12_11_contract_preserves_scientific_scope() -> None:
    text = (ROOT / "docs/P10_SD40_BOUNDED_PUBLIC_IDENTITY_CORRECTION_CONTRACT.md").read_text().lower(); assert "twenty-eight other files" in text and "docstring-only publication-identity correction" in text and "does not rerun quick, full, ds1" in text and "f03 and f15 remain open" in text
def test_sd12_12_private_provenance_is_not_publicly_redistributed() -> None: assert not (ROOT / "provenance").exists()
def test_sd12_13_no_distribution_envelope_inside_source_tree() -> None: assert not list(ROOT.glob("dist/*.whl")) and not list(ROOT.glob("dist/*.tar.gz"))
def test_sd12_14_version_remains_rc1() -> None: assert tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"] == "0.1.0rc1"
def test_sd12_15_readme_states_durable_public_identity_and_bounded_qualification() -> None:
    text = (ROOT / "README.md").read_text(); assert "publication-durable software-only release candidate" in text and "Operational publication authority is deliberately not encoded" in text and "No finite suite proves universal correctness" in text
def test_sd12_16_build_helper_enforces_sd40_recipe() -> None:
    text = (ROOT / "scripts/build_distributions.py").read_text(); assert 'EXPECTED_STATUS = "PUBLICATION_DURABLE_SOFTWARE_ONLY_RC1"' in text and 'EXPECTED_SETUPTOOLS = "84.0.0"' in text
