#!/usr/bin/env python3
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import tomllib
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
FORBIDDEN_SEGMENTS = {"paper", "evidence", "provenance", "reports"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}
REQUIRED_WHEEL = {
    "cdrse/__init__.py", "cdrse/cli.py", "cdrse/py.typed",
    "cdrse/schema_files/problem.schema.json", "cdrse/schema_files/certificate.schema.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_name(name: str) -> bool:
    pure = PurePosixPath(name.replace("\\", "/"))
    return not pure.is_absolute() and ".." not in pure.parts


def has_forbidden_segment(name: str) -> bool:
    return bool(set(PurePosixPath(name).parts) & FORBIDDEN_SEGMENTS)


def verify_record(z: ZipFile, record_name: str) -> None:
    rows = list(csv.reader(io.StringIO(z.read(record_name).decode("utf-8"))))
    mapped = {row[0]: row[1:] for row in rows}
    if set(mapped) != set(z.namelist()):
        raise SystemExit("wheel RECORD member set mismatch")
    for name in z.namelist():
        digest, size = mapped[name]
        if name == record_name:
            if digest or size:
                raise SystemExit("wheel RECORD self-row is not empty")
            continue
        payload = z.read(name)
        expected = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
        if digest != f"sha256={expected}" or size != str(len(payload)):
            raise SystemExit(f"wheel RECORD mismatch: {name}")


def main() -> int:
    wheels = sorted(DIST.glob("*.whl"))
    sdists = sorted(DIST.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("expected exactly one wheel and one sdist")
    wheel = wheels[0]
    with ZipFile(wheel) as z:
        if z.testzip() is not None:
            raise SystemExit("wheel CRC failed")
        names = z.namelist()
        if any(not safe_name(name) for name in names):
            raise SystemExit("unsafe wheel path")
        if any(has_forbidden_segment(name) for name in names):
            raise SystemExit("deferred-content path leaked into wheel")
        if any(Path(name).suffix in FORBIDDEN_SUFFIXES for name in names):
            raise SystemExit("compiled cache leaked into wheel")
        missing = sorted(REQUIRED_WHEEL - set(names))
        if missing:
            raise SystemExit(f"wheel missing files: {missing}")
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = z.read(metadata_name).decode("utf-8")
        version = tomllib.loads((ROOT / "pyproject.toml").read_text())['project']['version']
        for token in (
            "Name: cdrs-e", f"Version: {version}",
            "Author-email: Antonio Clim <Antonio.clim@csie.ase.ro>",
            "License-Expression: Apache-2.0", "License-File: LICENSE", "License-File: NOTICE",
        ):
            if token not in metadata:
                raise SystemExit(f"wheel metadata missing {token}")
        licences = {name.rsplit('/', 1)[-1] for name in names if '.dist-info/licenses/' in name}
        if licences != {"LICENSE", "NOTICE"}:
            raise SystemExit(f"unexpected wheel licence payload: {sorted(licences)}")
        record_name = next(name for name in names if name.endswith(".dist-info/RECORD"))
        verify_record(z, record_name)
    sdist = sdists[0]
    with tarfile.open(sdist, "r:gz") as t:
        members = t.getmembers()
        if any(not safe_name(m.name) for m in members):
            raise SystemExit("unsafe sdist path")
        if any(has_forbidden_segment(m.name) for m in members):
            raise SystemExit("deferred-content path leaked into sdist")
        names = {m.name for m in members}
        root = sorted(names)[0].split('/', 1)[0]
        for required in ("pyproject.toml", "README.md", "LICENSE", "NOTICE", "src/cdrse/cli.py", "PUBLIC_RELEASE_LICENCE_GATE.md"):
            if f"{root}/{required}" not in names:
                raise SystemExit(f"sdist missing {required}")
    result = {
        "status": "PASS", "deferred_path_count": 0,
        "wheel": {"file": wheel.name, "bytes": wheel.stat().st_size, "sha256": sha256(wheel)},
        "sdist": {"file": sdist.name, "bytes": sdist.stat().st_size, "sha256": sha256(sdist)},
    }
    out = ROOT / "build" / "verification"
    out.mkdir(parents=True, exist_ok=True)
    (out / "distribution_verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
