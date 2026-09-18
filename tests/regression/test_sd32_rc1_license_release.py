from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import tomllib
ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.0rc1"
REPOSITORY = "https://github.com/antonioclim/cdrs-e"
VOLATILE_KEYS = {"public_release_authorized", "public_release_authorised", "remote_actions_performed", "remote_actions_authorised", "tag_authorized", "github_release_authorized", "github_publication_authorized", "github_actions_authorized", "zenodo_deposit_authorized", "doi_reservation_authorized", "pypi_upload_authorized", "submission_authorized"}
def _json(path: str) -> dict: return json.loads((ROOT / path).read_text(encoding="utf-8"))
def _cli(*args: str) -> dict:
    return json.loads(subprocess.run([sys.executable, "-m", "cdrse", *args], cwd=ROOT, text=True, capture_output=True, check=True).stdout)
def test_sd32_01_version_surfaces_are_consistent() -> None:
    assert tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"] == VERSION
    assert f'__version__ = "{VERSION}"' in (ROOT / "src/cdrse/_version.py").read_text(); assert f'version: "{VERSION}"' in (ROOT / "CITATION.cff").read_text(); assert _json("codemeta.json")["version"] == VERSION
def test_sd32_02_apache_licence_files_exist() -> None: assert "Apache License" in (ROOT / "LICENSE").read_text() and "Copyright 2026 Antonio Clim" in (ROOT / "NOTICE").read_text()
def test_sd32_03_pep621_licence_and_author_email() -> None:
    p = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]; assert p["license"] == "Apache-2.0" and p["license-files"] == ["LICENSE", "NOTICE"] and p["authors"] == [{"name": "Antonio Clim", "email": "Antonio.clim@csie.ase.ro"}]
def test_sd32_04_citation_metadata_has_durable_repository_identity() -> None:
    t = (ROOT / "CITATION.cff").read_text(); assert "license: Apache-2.0" in t and "0000-0003-4745-0431" in t and f'repository-code: "{REPOSITORY}"' in t
def test_sd32_05_codemeta_is_licensed_and_publication_durable() -> None:
    d = _json("codemeta.json"); assert d["license"] == "https://spdx.org/licenses/Apache-2.0" and d["codeRepository"] == REPOSITORY and "identifier" not in d and "doi" not in d
def test_sd32_06_release_gates_separate_artifact_state_from_operations() -> None:
    g = _json("release-gates.json"); assert g["licence_selected"] is True and g["licence_spdx"] == "Apache-2.0" and g["operational_authority_embedded"] is False and VOLATILE_KEYS.isdisjoint(g)
def test_sd32_07_release_track_and_tag_are_bound() -> None:
    g = _json("release-gates.json"); assert g["release_track"] == "R-B_PROMOTED_RC" and g["publication_identity"]["tag"] == "v0.1.0rc1"
def test_sd32_08_build_recipe_is_publication_durable_and_fixed_epoch() -> None:
    r = _json("build-recipe.json"); assert r["software_version"] == VERSION and r["candidate_status"] == "PUBLICATION_DURABLE_SOFTWARE_ONLY_RC1" and r["source_date_epoch"] == 1789689600
def test_sd32_09_build_script_enforces_sd40_recipe() -> None:
    t = (ROOT / "scripts/build_distributions.py").read_text(); assert 'recipe["software_version"] != "0.1.0rc1"' in t and 'EXPECTED_STATUS = "PUBLICATION_DURABLE_SOFTWARE_ONLY_RC1"' in t
def test_sd32_10_cli_version_reports_durable_release_identity() -> None:
    p = _cli("version"); assert p["version"] == VERSION and p["release_candidate"] is True and p["publication_profile"] == "publication-durable" and p["canonical_repository"] == REPOSITORY and "public_release" not in p
def test_sd32_11_self_check_reports_same_release_identity() -> None:
    p = _cli("self-check", "--json"); assert p["status"] == "PASS" and p["version"] == VERSION and p["publication_profile"] == "publication-durable" and p["canonical_repository"] == REPOSITORY and "public_release" not in p
def test_sd32_12_scientific_payload_identity_is_transparently_bounded() -> None:
    r = _json("release/ALGORITHMIC_PAYLOAD_IDENTITY.json"); init = next(x for x in r["files"] if x["path"] == "src/cdrse/__init__.py"); others = [x for x in r["files"] if x["path"] != "src/cdrse/__init__.py"]; assert r["all_identical"] is False and r["file_count"] == 29 and r["byte_identical_count"] == 28 and r["docstring_only_correction_count"] == 1 and len(others) == 28 and all(x["identical_to_sd37"] for x in others) and init["identical_to_sd37"] is False and init["only_first_line_changed"] is True and init["bytes_after_first_line_identical"] is True and init["ast_excluding_module_docstring_identical"] is True
def test_sd32_13_result_contract_title_uses_rc1_identity() -> None: assert VERSION in _json("src/cdrse/schema_files/result_contract.schema.json")["title"]
def test_sd32_14_manifest_and_distribution_verifier_enforce_clean_surface() -> None:
    m = (ROOT / "MANIFEST.in").read_text(); v = (ROOT / "scripts/verify_distribution.py").read_text(); assert "prune provenance" in m and "prune reports" in m and "FORBIDDEN_SEGMENTS" in v and "verify_record" in v
def test_sd32_15_private_remote_operation_plans_are_absent() -> None:
    for p in ("release/GITHUB_PUBLIC_REPOSITORY_PLAN.json", "release/ZENODO_DEPOSIT_PLAN.json", "release/REMOTE_AUTHORITY_BOUNDARY.md", "release/zenodo-metadata-DRAFT.json", "release/RELEASE_NOTES_v0.1.0rc1_DRAFT.md"): assert not (ROOT / p).exists()
def test_sd32_16_publication_identity_is_complete() -> None:
    p = _json("release/PUBLICATION_IDENTITY.json"); assert p["canonical_repository_url"] == REPOSITORY and p["tag"] == "v0.1.0rc1" and p["release_channel"] == "release-candidate"
def test_sd32_17_source_snapshot_has_no_fabricated_doi() -> None:
    assert "doi:" not in (ROOT / "CITATION.cff").read_text().lower(); assert "doi" not in _json("codemeta.json"); assert _json("release/PUBLICATION_IDENTITY.json")["doi_embedded_in_source_snapshot"] is False
def test_sd32_18_public_release_gate_is_artifact_stable() -> None:
    t = " ".join((ROOT / "PUBLIC_RELEASE_LICENCE_GATE.md").read_text().split()); assert "Apache License 2.0 has been selected for and applies" in t and "Operational authority" in t and "external to this artefact" in t
def test_sd32_19_no_distribution_envelope_is_committed_inside_source() -> None: assert not list(ROOT.glob("dist/*.whl")) and not list(ROOT.glob("dist/*.tar.gz"))
def test_sd32_20_public_metadata_contains_no_volatile_authority_keys() -> None:
    for path in ("release-gates.json", "build-recipe.json", "release/PUBLIC_SURFACE_SCOPE.json", "release/PUBLICATION_IDENTITY.json"): assert VOLATILE_KEYS.isdisjoint(_json(path))
def test_sd32_21_licence_scope_excludes_deferred_content() -> None:
    t = (ROOT / "LICENSING.md").read_text(); assert "Apache License 2.0 applies to the software work" in t and all(f"`{x}/`" in t for x in ("paper", "evidence", "provenance", "reports"))
