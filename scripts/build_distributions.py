#!/usr/bin/env python3
from __future__ import annotations

from importlib.metadata import version
import copy
import gzip
import io
import json
import os
from pathlib import Path
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RECIPE_PATH = ROOT / "build-recipe.json"
EXPECTED_SETUPTOOLS = "84.0.0"
EXPECTED_SOURCE_DATE_EPOCH = "1789689600"
EXPECTED_STATUS = "PREPARED_CANDIDATE_RC3"
FORBIDDEN_TOP_LEVEL = {"paper", "evidence", "provenance", "reports"}


def validate_public_surface() -> None:
    leaked = [name for name in sorted(FORBIDDEN_TOP_LEVEL) if (ROOT / name).exists()]
    if leaked:
        raise RuntimeError(f"deferred-content paths present: {leaked}")


def validate_build_environment() -> dict[str, str]:
    validate_public_surface()
    recipe = json.loads(RECIPE_PATH.read_text(encoding="utf-8"))
    if recipe["software_version"] != "0.1.0rc3":
        raise RuntimeError("build-recipe.json does not describe 0.1.0rc3")
    if recipe["candidate_status"] != EXPECTED_STATUS:
        raise RuntimeError("build recipe is not the prepared rc3 software-only recipe")
    if recipe["planned_derivation_method"] != "FRESH_EXACT_BACKEND_BUILD" or recipe["old_qualified_assets_permitted_as_build_inputs"] is not False:
        raise RuntimeError("rc3 requires a fresh exact-backend build; historical envelopes are forbidden")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if project["version"] != "0.1.0rc3" or (ROOT / "src/cdrse/_version.py").read_text(encoding="utf-8") != '__version__ = "0.1.0rc3"\n':
        raise RuntimeError("source and build-recipe identities disagree")
    if json.loads((ROOT / "codemeta.json").read_text(encoding="utf-8"))["version"] != "0.1.0rc3" or 'version: "0.1.0rc3"' not in (ROOT / "CITATION.cff").read_text(encoding="utf-8"):
        raise RuntimeError("citation metadata and build-recipe identities disagree")
    if recipe["source_date_epoch"] != int(EXPECTED_SOURCE_DATE_EPOCH):
        raise RuntimeError("build recipe and fixed normalisation epoch disagree")
    if recipe["setuptools_version"] != EXPECTED_SETUPTOOLS:
        raise RuntimeError("build recipe and executable build script disagree")
    observed = version("setuptools")
    if observed != EXPECTED_SETUPTOOLS:
        raise RuntimeError(f"setuptools {EXPECTED_SETUPTOOLS} is required; observed {observed}")
    supplied_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if supplied_epoch is None:
        os.environ["SOURCE_DATE_EPOCH"] = EXPECTED_SOURCE_DATE_EPOCH
    elif supplied_epoch != EXPECTED_SOURCE_DATE_EPOCH:
        raise RuntimeError(
            f"SOURCE_DATE_EPOCH must equal {EXPECTED_SOURCE_DATE_EPOCH}; observed {supplied_epoch}"
        )
    return {"setuptools": observed, "source_date_epoch": os.environ["SOURCE_DATE_EPOCH"]}


def normalise_sdist(path: Path, *, epoch: int) -> None:
    rows: list[tuple[tarfile.TarInfo, bytes | None]] = []
    with tarfile.open(path, "r:gz") as source:
        for member in source.getmembers():
            payload = source.extractfile(member).read() if member.isfile() else None
            rows.append((member, payload))
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as target:
        for member, payload in sorted(rows, key=lambda row: row[0].name):
            fixed = copy.copy(member)
            fixed.mtime = epoch
            fixed.uid = fixed.gid = 0
            fixed.uname = fixed.gname = ""
            fixed.pax_headers = {}
            target.addfile(fixed, io.BytesIO(payload) if payload is not None else None)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=epoch) as compressed:
            compressed.write(tar_buffer.getvalue())


def main() -> int:
    recipe = validate_build_environment()
    import setuptools.build_meta as backend
    # Preserve every earlier build, failed output and partial. Build in a fresh copy.
    occupied = [p for p in (ROOT / "build", DIST) if p.exists()]
    occupied += list(ROOT.glob("*.egg-info")) + list((ROOT / "src").glob("*.egg-info"))
    if occupied:
        raise RuntimeError("build destinations already exist; preserve them and use a fresh source copy")
    DIST.mkdir()
    old = Path.cwd()
    try:
        os.chdir(ROOT)
        wheel = backend.build_wheel(str(DIST))
        sdist = backend.build_sdist(str(DIST))
        normalise_sdist(DIST / sdist, epoch=int(EXPECTED_SOURCE_DATE_EPOCH))
    finally:
        os.chdir(old)
    print(f"setuptools={recipe['setuptools']}")
    print(f"SOURCE_DATE_EPOCH={recipe['source_date_epoch']}")
    print(wheel)
    print(sdist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
