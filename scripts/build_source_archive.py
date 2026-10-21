#!/usr/bin/env python3
"""Construct a deterministic source archive from a frozen working copy.

Administrative packaging only. This script does not run project modules or tests.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import stat
import time
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
EPOCH = 1789689600
VERSION = "0.1.0"
ARCHIVE_ROOT = "CDRS_E_0.1.0_SOURCE_AND_TESTS"
FORBIDDEN = {"paper", "evidence", "provenance", "reports"}
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist", ".venv", ".git"}
GENERATED_NAMES = {"SOURCE_ARCHIVE_README.md", "SOURCE_MANIFEST_SHA256.json"}
MAX_SOURCE_BYTES = 16 * 1024 * 1024


def public_files(root: Path) -> list[Path]:
    rows = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if rel.parts[0] in FORBIDDEN or any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if any(part.endswith(".egg-info") for part in rel.parts) or path.name.startswith(".coverage") or path.name in {"coverage.json", "coverage.xml"}:
            continue
        if path.is_symlink():
            raise RuntimeError(f"symlink is not a source member: {rel.as_posix()}")
        if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
            continue
        # These two files are an archive envelope, not source-tree members.
        if len(rel.parts) == 1 and rel.name.casefold() in {n.casefold() for n in GENERATED_NAMES}:
            if rel.name not in GENERATED_NAMES:
                raise RuntimeError("reserved generated-name case collision")
            continue
        rows.append(path)
    names = [p.relative_to(root).as_posix() for p in rows]
    if len(names) != len(set(names)) or len(names) != len({n.casefold() for n in names}):
        raise RuntimeError("duplicate or case-colliding source path")
    return sorted(rows, key=lambda p: p.relative_to(root).as_posix())


def build_source_archive(output: Path, *, root: Path = ROOT) -> dict[str, object]:
    root = root.resolve()
    output = output.resolve()
    if output.exists():
        raise FileExistsError("preserve previous output; use a fresh destination")
    for name in FORBIDDEN:
        if (root / name).exists():
            raise RuntimeError(f"forbidden public path exists: {name}")
    recipe = json.loads((root / "build-recipe.json").read_text(encoding="utf-8"))
    if recipe["software_version"] != VERSION or recipe["candidate_status"] != "PREPARED_RELEASE_010" or recipe["source_date_epoch"] != EPOCH:
        raise RuntimeError("source archive recipe does not identify prepared 0.1.0")
    files = public_files(root)
    payloads = {}
    total = 0
    for path in files:
        if path.resolve() == output:
            raise RuntimeError("output would be included as source")
        payload = path.read_bytes()
        total += len(payload)
        if total > MAX_SOURCE_BYTES:
            raise RuntimeError("source material exceeds the administrative packaging bound")
        payloads[path.relative_to(root).as_posix()] = payload
    manifest = {name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()} for name, payload in payloads.items()}
    generated = {
        "SOURCE_ARCHIVE_README.md": (
            "# CDRS-E 0.1.0 source-and-tests archive\n\n"
            "The source profile was prepared with execution UNRUN. Later execution or publication must be established by separate receipts bound to these bytes. "
            "The two SOURCE_* envelope members are generated and excluded from the source manifest. "
            "Operational publication authority is external to this artefact.\n"
        ).encode("utf-8"),
        "SOURCE_MANIFEST_SHA256.json": (json.dumps({"schema": "CDRSE_RC3_SOURCE_MANIFEST_V1", "files": manifest}, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    }
    if set(payloads) & set(generated):
        raise RuntimeError("generated-name collision")
    output.parent.mkdir(parents=True, exist_ok=True)
    dt = time.gmtime(EPOCH)[:6]
    with ZipFile(output, "x", compression=ZIP_DEFLATED, compresslevel=9) as z:
        info = ZipInfo(ARCHIVE_ROOT + "/", date_time=dt)
        info.external_attr = (stat.S_IFDIR | 0o755) << 16 | 0x10
        z.writestr(info, b"")
        for rel, payload in sorted({**payloads, **generated}.items()):
            info = ZipInfo(f"{ARCHIVE_ROOT}/{rel}", date_time=dt)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            z.writestr(info, payload)
    return {"file": output.name, "bytes": output.stat().st_size, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "source_files": len(files), "generated_files": len(generated)}


def main() -> int:
    print(json.dumps(build_source_archive(ROOT / "dist" / f"{ARCHIVE_ROOT}.zip"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
