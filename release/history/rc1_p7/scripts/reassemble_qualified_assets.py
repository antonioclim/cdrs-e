#!/usr/bin/env python3
from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import time
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
EPOCH = 1789689600
DIST_INFO = "cdrs_e-0.1.0rc1.dist-info"
SDIST_ROOT = "cdrs_e-0.1.0rc1"
FORBIDDEN = {"paper", "evidence", "provenance", "reports"}
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist", ".venv"}


def digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_repo_files() -> list[Path]:
    rows = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if rel.parts[0] in FORBIDDEN or any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(path)
    return sorted(rows, key=lambda p: p.relative_to(ROOT).as_posix())


def fixed_zip(output: Path, rows: dict[str, bytes]) -> None:
    dt = time.gmtime(EPOCH)[:6]
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        for name, payload in sorted(rows.items()):
            info = ZipInfo(name, date_time=dt)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, payload)


def replace_long_description(metadata: bytes) -> bytes:
    headers = metadata.decode("utf-8").split("\n\n", 1)[0].splitlines()
    headers = [line for line in headers if not line.startswith("Project-URL:")]
    urls = [
        "Project-URL: Homepage, https://github.com/antonioclim/cdrs-e",
        "Project-URL: Repository, https://github.com/antonioclim/cdrs-e",
        "Project-URL: Issues, https://github.com/antonioclim/cdrs-e/issues",
        "Project-URL: Changelog, https://github.com/antonioclim/cdrs-e/blob/main/CHANGELOG.md",
    ]
    return ("\n".join(headers + urls) + "\n\n" + (ROOT / "README.md").read_text(encoding="utf-8")).encode()


def reassemble_wheel(input_wheel: Path, output: Path) -> dict[str, object]:
    with ZipFile(input_wheel) as z:
        rows = {name: z.read(name) for name in z.namelist() if not name.endswith("/")}
    for name in list(rows):
        if name == f"{DIST_INFO}/RECORD" or name.startswith("cdrse/"):
            rows.pop(name)
    for path in sorted((ROOT / "src/cdrse").rglob("*")):
        if path.is_file() and path.suffix not in {".pyc", ".pyo"} and "__pycache__" not in path.parts:
            rows[path.relative_to(ROOT / "src").as_posix()] = path.read_bytes()
    rows[f"{DIST_INFO}/licenses/LICENSE"] = (ROOT / "LICENSE").read_bytes()
    rows[f"{DIST_INFO}/licenses/NOTICE"] = (ROOT / "NOTICE").read_bytes()
    rows[f"{DIST_INFO}/METADATA"] = replace_long_description(rows[f"{DIST_INFO}/METADATA"])
    rows[f"{DIST_INFO}/WHEEL"] = (
        "Wheel-Version: 1.0\n"
        "Generator: P10-SD40 deterministic reassembly from qualified P10-SD37 wheel\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n\n"
    ).encode()
    record_rows = []
    for name, payload in sorted(rows.items()):
        record_rows.append([name, f"sha256={digest(payload)}", str(len(payload))])
    record_rows.append([f"{DIST_INFO}/RECORD", "", ""])
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(record_rows)
    rows[f"{DIST_INFO}/RECORD"] = stream.getvalue().encode()
    fixed_zip(output, rows)
    return {"file": output.name, "bytes": output.stat().st_size, "sha256": sha256(output), "members": len(rows)}


def _metadata_from_original_sdist(original: Path) -> tuple[bytes, dict[str, bytes]]:
    with tarfile.open(original, "r:gz") as t:
        source = {}
        pkg_info = b""
        for member in t.getmembers():
            if not member.isfile():
                continue
            rel = PurePosixPath(member.name)
            if len(rel.parts) < 2:
                continue
            sub = PurePosixPath(*rel.parts[1:]).as_posix()
            payload = t.extractfile(member).read()
            if sub == "PKG-INFO":
                pkg_info = replace_long_description(payload)
            elif sub.startswith("src/cdrs_e.egg-info/"):
                source[sub] = payload
        return pkg_info, source


def reassemble_sdist(input_sdist: Path, output: Path) -> dict[str, object]:
    pkg_info, egg_info = _metadata_from_original_sdist(input_sdist)
    rows: dict[str, bytes] = {}
    for path in public_repo_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(".github/") or rel in {".gitignore", "Makefile", "CONTRIBUTING.md", "SECURITY.md", "requirements-dev.txt", "requirements-lock.txt", "environment.yml"} or rel.startswith("containers/"):
            continue
        rows[rel] = path.read_bytes()
    rows["PKG-INFO"] = pkg_info
    egg_info["src/cdrs_e.egg-info/PKG-INFO"] = pkg_info
    sources = sorted(set(rows) | set(egg_info))
    egg_info["src/cdrs_e.egg-info/SOURCES.txt"] = ("\n".join(sources) + "\n").encode()
    rows.update(egg_info)
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as t:
        root = tarfile.TarInfo(SDIST_ROOT)
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        root.mtime = EPOCH
        root.uid = root.gid = 0
        t.addfile(root)
        dirs = set()
        for rel in rows:
            p = PurePosixPath(rel)
            for i in range(1, len(p.parts)):
                dirs.add(PurePosixPath(*p.parts[:i]).as_posix())
        for rel in sorted(dirs):
            info = tarfile.TarInfo(f"{SDIST_ROOT}/{rel}")
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            info.mtime = EPOCH
            info.uid = info.gid = 0
            t.addfile(info)
        for rel, payload in sorted(rows.items()):
            info = tarfile.TarInfo(f"{SDIST_ROOT}/{rel}")
            info.size = len(payload)
            info.mode = 0o644
            info.mtime = EPOCH
            info.uid = info.gid = 0
            t.addfile(info, io.BytesIO(payload))
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=EPOCH) as gz:
            gz.write(tar_buffer.getvalue())
    return {"file": output.name, "bytes": output.stat().st_size, "sha256": sha256(output), "members": len(rows)}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualified-wheel", type=Path, required=True)
    parser.add_argument("--qualified-sdist", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    wheel = args.output_dir / "cdrs_e-0.1.0rc1-py3-none-any.whl"
    sdist = args.output_dir / "cdrs_e-0.1.0rc1.tar.gz"
    result = {
        "wheel": reassemble_wheel(args.qualified_wheel, wheel),
        "sdist": reassemble_sdist(args.qualified_sdist, sdist),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
