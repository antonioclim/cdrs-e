from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tomllib
ROOT = Path(__file__).resolve().parents[2]
SETUPTOOLS = "84.0.0"
EPOCH = 1789689600
SETUPTOOLS_SHA = "51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
VOLATILE_KEYS = {"public_release_authorized", "public_release_authorised", "remote_actions_performed", "remote_actions_authorised", "tag_authorized", "github_release_authorized", "github_publication_authorized", "github_actions_authorized", "zenodo_deposit_authorized", "doi_reservation_authorized", "pypi_upload_authorized", "submission_authorized"}
def _json(path: str) -> dict: return json.loads((ROOT / path).read_text(encoding="utf-8"))
def test_sd8_historical_build_lineage_is_publicly_bounded() -> None:
    lock = _json("release/TOOLCHAIN_LOCK.json"); assert lock["canonical_backend"] == {"name": "setuptools", "version": SETUPTOOLS}
def test_current_source_candidate_backend_is_exactly_pinned() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text()); assert data["build-system"]["requires"] == [f"setuptools=={SETUPTOOLS}"] and data["build-system"]["build-backend"] == "setuptools.build_meta"
def test_current_recipe_is_machine_readable_bounded_and_publication_durable() -> None:
    r = _json("build-recipe.json"); assert r["software_version"] == "0.1.0rc1" and r["candidate_status"] == "PUBLICATION_DURABLE_SOFTWARE_ONLY_RC1" and r["source_date_epoch"] == EPOCH and r["scientific_source_changed"] is False and r["exact_backend_reacquired_or_executed_in_p10_sd40"] is False
def test_current_build_lock_records_official_release_hashes() -> None:
    lines = [x for x in (ROOT / "build-system.lock.txt").read_text().splitlines() if x and not x.startswith("#")]; assert lines == ["setuptools==84.0.0 --hash=sha256:51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670", "pip==26.2.1 --hash=sha256:71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e"]
def test_build_script_enforces_current_backend_epoch_and_surface() -> None:
    path = ROOT / "scripts/build_distributions.py"; spec = importlib.util.spec_from_file_location("build", path); assert spec and spec.loader; module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); assert module.EXPECTED_SETUPTOOLS == SETUPTOOLS and module.EXPECTED_SOURCE_DATE_EPOCH == str(EPOCH) and module.EXPECTED_STATUS == "PUBLICATION_DURABLE_SOFTWARE_ONLY_RC1" and callable(module.validate_public_surface)
def test_release_gates_are_durable_for_software_only_rc1() -> None:
    g = _json("release-gates.json"); assert g["candidate_status"] == "PUBLICATION_DURABLE_SOFTWARE_ONLY_RC1" and g["public_surface"]["deferred_path_count"] == 0 and g["operational_authority_embedded"] is False and VOLATILE_KEYS.isdisjoint(g)
