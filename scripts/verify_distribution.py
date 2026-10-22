#!/usr/bin/env python3
"""Bounded, fail-closed wheel/sdist structure and source-byte verification.

This is an administrative distribution check, not scientific execution evidence.
"""
from __future__ import annotations
import base64
import csv
from email.parser import Parser
import hashlib
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import tarfile
import tomllib
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
FORBIDDEN_SEGMENTS = {"paper", "evidence", "provenance", "reports"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}
MAX_MEMBERS = 4096
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024


def safe_name(name: str) -> bool:
    if not isinstance(name, str) or not name or "\\" in name:
        return False
    if any(ord(c) < 32 or c in ':<>|"?*' for c in name):
        return False
    text = name[:-1] if name.endswith("/") else name
    pure = PurePosixPath(text)
    if not text or pure.is_absolute() or PureWindowsPath(text).drive:
        return False
    devices = {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)}, *{f"LPT{i}" for i in range(1, 10)}}
    return all(p not in {"", ".", ".."} and not p.endswith((" ", ".")) and p.split(".", 1)[0].upper() not in devices for p in text.split("/")) and pure.as_posix() == text


def _validate_names(names: list[str]) -> None:
    if len(names) > MAX_MEMBERS or any(not safe_name(n) for n in names):
        raise ValueError("unsafe archive path or member limit")
    canonical = [n.rstrip("/") for n in names]
    if len(canonical) != len(set(canonical)) or len(canonical) != len({n.casefold() for n in canonical}):
        raise ValueError("duplicate or case-colliding archive members")
    for name in canonical:
        parts = PurePosixPath(name).parts
        if set(parts) & FORBIDDEN_SEGMENTS or PurePosixPath(name).suffix in FORBIDDEN_SUFFIXES:
            raise ValueError("deferred-content or compiled-cache path")


def validate_zip_members(z: ZipFile) -> list[str]:
    infos = z.infolist()
    names = [i.filename for i in infos]
    _validate_names(names)
    if any(i.flag_bits & 1 for i in infos):
        raise ValueError("encrypted ZIP member")
    if any(stat.S_IFMT(i.external_attr >> 16) not in {0, stat.S_IFREG, stat.S_IFDIR} for i in infos):
        raise ValueError("ZIP special member or symbolic link")
    if any(i.file_size > MAX_MEMBER_BYTES for i in infos) or sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
        raise ValueError("ZIP decompression bound")
    if z.testzip() is not None:
        raise ValueError("ZIP CRC mismatch")
    return names


def validate_tar_members(members: list[tarfile.TarInfo]) -> str:
    _validate_names([m.name for m in members])
    if any(not (m.isfile() or m.isdir()) for m in members):
        raise ValueError("sdist link or special member")
    if any(m.size > MAX_MEMBER_BYTES for m in members) or sum(m.size for m in members) > MAX_TOTAL_BYTES:
        raise ValueError("sdist decompression bound")
    roots = {PurePosixPath(m.name).parts[0] for m in members}
    if len(roots) != 1:
        raise ValueError("sdist must have exactly one root")
    return next(iter(roots))


def verify_record(z: ZipFile, record_name: str) -> None:
    rows = list(csv.reader(io.StringIO(z.read(record_name).decode("utf-8"))))
    if any(len(row) != 3 for row in rows):
        raise ValueError("malformed wheel RECORD row")
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError("duplicate wheel RECORD row")
    mapped = {row[0]: row[1:] for row in rows}
    if set(mapped) != set(z.namelist()):
        raise ValueError("wheel RECORD member set mismatch")
    for name in z.namelist():
        digest, size = mapped[name]
        if name == record_name:
            if digest or size:
                raise ValueError("wheel RECORD self-row is not empty")
            continue
        payload = z.read(name)
        expected = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode("ascii")
        if digest != f"sha256={expected}" or size != str(len(payload)):
            raise ValueError(f"wheel RECORD mismatch: {name}")


def source_package() -> dict[str, bytes]:
    package = ROOT / "src" / "cdrse"
    rows = {}
    for p in sorted(package.rglob("*")):
        if "__pycache__" in p.parts or p.suffix in FORBIDDEN_SUFFIXES:
            continue
        if p.is_symlink():
            raise ValueError("source package contains a symlink")
        if p.is_file():
            rows['cdrse/' + p.relative_to(package).as_posix()] = p.read_bytes()
    return rows


def verify_wheel_licences(z: ZipFile, expected_info: str, source_root: Path = ROOT) -> None:
    """Bind the two declared licence payloads to exact paths and source bytes.

    A valid RECORD only binds a wheel to itself. It does not establish that
    its licence text is the text selected in the frozen source tree.
    """
    expected = {expected_info + "licenses/" + name: source_root / name for name in ("LICENSE", "NOTICE")}
    names = z.namelist()
    actual = [
        name for name in names
        if name.startswith(expected_info + "licenses/")
        or (name.startswith(expected_info) and PurePosixPath(name).name in {"LICENSE", "NOTICE"})
    ]
    if len(actual) != len(expected) or set(actual) != set(expected):
        raise ValueError("wheel licence paths or multiplicity mismatch")
    for name, source in expected.items():
        if source.is_symlink() or not source.is_file() or z.read(name) != source.read_bytes():
            raise ValueError(f"wheel licence bytes differ from the selected source: {name}")


def main() -> int:
    wheels = sorted(DIST.glob("*.whl"))
    sdists = sorted(DIST.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("expected exactly one wheel and one sdist")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    expected_info = f"cdrs_e-{version}.dist-info/"
    package = source_package()
    wheel, sdist = wheels[0], sdists[0]
    with ZipFile(wheel) as z:
        names = validate_zip_members(z)
        if any(n.endswith("/") for n in names):
            raise ValueError("wheel contains unexpected directory entries")
        if any(not (n.startswith('cdrse/') or n.startswith(expected_info)) for n in names):
            raise ValueError("wheel contains an unexpected top-level surface")
        infos = {n.split('/', 1)[0] for n in names if '.dist-info/' in n}
        if infos != {expected_info.rstrip('/')}:
            raise ValueError("wheel distribution metadata identity mismatch")
        metadata_name = expected_info + 'METADATA'
        record_name = expected_info + 'RECORD'
        headers = Parser().parsestr(z.read(metadata_name).decode('utf-8'))
        for key, value in {'Name':'cdrs-e', 'Version':version, 'Author-email':'Antonio Clim <Antonio.clim@csie.ase.ro>', 'License-Expression':'Apache-2.0'}.items():
            if headers.get_all(key) != [value]:
                raise ValueError(f"wheel metadata mismatch: {key}")
        if set(headers.get_all('License-File', [])) != {'LICENSE','NOTICE'}:
            raise ValueError("wheel licence declarations mismatch")
        verify_wheel_licences(z, expected_info)
        actual_package = {n:z.read(n) for n in names if n.startswith('cdrse/')}
        if actual_package != package:
            raise ValueError("wheel package bytes differ from the selected source")
        verify_record(z, record_name)
    with tarfile.open(sdist, "r:gz") as t:
        members = t.getmembers()
        root = validate_tar_members(members)
        if root != f'cdrs_e-{version}':
            raise ValueError("sdist root identity mismatch")
        by_name = {m.name:m for m in members}
        for required in ['pyproject.toml','README.md','LICENSE','NOTICE','LICENSING.md','PUBLIC_RELEASE_LICENCE_GATE.md','.github/workflows/ci.yml']:
            m = by_name.get(root+'/'+required)
            if m is None or not m.isfile() or t.extractfile(m).read() != (ROOT/required).read_bytes():
                raise ValueError(f"sdist missing or differing source file: {required}")
        actual_package = {n[len(root+'/src/'):]:t.extractfile(m).read() for n,m in by_name.items() if n.startswith(root+'/src/cdrse/') and m.isfile()}
        if actual_package != package:
            raise ValueError("sdist package bytes differ from the selected source")
    result = {'status':'PASS_ADMINISTRATIVE_DISTRIBUTION_CHECK', 'scientific_execution':False, 'scope':'archive structure, metadata, RECORD and literal package-byte binding to the selected source', 'wheel':{'file':wheel.name,'bytes':wheel.stat().st_size,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()},'sdist':{'file':sdist.name,'bytes':sdist.stat().st_size,'sha256':hashlib.sha256(sdist.read_bytes()).hexdigest()}}
    out = ROOT/'build'/'verification'
    out.mkdir(parents=True, exist_ok=True)
    destination = out/'distribution_verification.json'
    with destination.open('x', encoding='utf-8') as f:
        f.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
