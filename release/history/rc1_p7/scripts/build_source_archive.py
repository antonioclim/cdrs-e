#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import time
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
EPOCH = 1789689600
ARCHIVE_ROOT = "CDRS_E_0.1.0rc1_P10SD40_PUBLICATION_DURABLE_SOURCE_AND_TESTS"
FORBIDDEN = {"paper", "evidence", "provenance", "reports"}
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist", ".venv"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def public_files(root: Path) -> list[Path]:
    rows = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if rel.parts[0] in FORBIDDEN or any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(path)
    return sorted(rows, key=lambda p: p.relative_to(root).as_posix())


def build_source_archive(output: Path, *, root: Path = ROOT) -> dict[str, object]:
    for name in FORBIDDEN:
        if (root / name).exists():
            raise RuntimeError(f"forbidden public path exists: {name}")
    files = public_files(root)
    manifest = {
        p.relative_to(root).as_posix(): {"bytes": p.stat().st_size, "sha256": sha256(p)}
        for p in files
    }
    generated = {
        "SOURCE_ARCHIVE_README.md": (
            "# CDRS-E P10-SD40 publication-durable software-only source archive\n\n"
            "This archive contains only the Apache-2.0 software surface. "
            "Manuscript, evidence, private provenance and generated reports are excluded. "
            "Operational publication authority is deliberately external to this public artefact.\n"
        ).encode(),
        "SOURCE_MANIFEST_SHA256.json": (json.dumps({"schema": "CDRSE_P10_SD40_SOURCE_MANIFEST_v1", "files": manifest}, indent=2, sort_keys=True) + "\n").encode(),
    }
    dt = time.gmtime(EPOCH)[:6]
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        root_info = ZipInfo(ARCHIVE_ROOT + "/", date_time=dt)
        root_info.external_attr = (0o40755 << 16) | 0x10
        z.writestr(root_info, b"")
        for p in files:
            rel = p.relative_to(root).as_posix()
            info = ZipInfo(f"{ARCHIVE_ROOT}/{rel}", date_time=dt)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes())
        for rel, payload in sorted(generated.items()):
            info = ZipInfo(f"{ARCHIVE_ROOT}/{rel}", date_time=dt)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, payload)
    return {"file": output.name, "bytes": output.stat().st_size, "sha256": sha256(output), "source_files": len(files), "generated_files": len(generated)}


def main() -> int:
    out = ROOT / "dist" / f"{ARCHIVE_ROOT}.zip"
    print(json.dumps(build_source_archive(out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
