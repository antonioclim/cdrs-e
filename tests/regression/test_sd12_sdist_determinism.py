from __future__ import annotations
import gzip, importlib.util, io, json
from pathlib import Path
import tarfile
ROOT = Path(__file__).resolve().parents[2]
def _module():
    path = ROOT / "scripts/build_distributions.py"
    spec = importlib.util.spec_from_file_location("sd12_build", path); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
def _synthetic(path: Path, *, mtime: int) -> None:
    payload = b"deterministic-sdist-test\n"; buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        info = tarfile.TarInfo("demo/file.txt"); info.size = len(payload); info.mtime = mtime; info.uid = 1000; info.gid = 1001; info.uname = "user"; info.gname = "group"; archive.addfile(info, io.BytesIO(payload))
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="demo.tar", mode="wb", fileobj=raw, mtime=mtime) as stream: stream.write(buffer.getvalue())
def test_sd12_f41_01_current_derivation_requires_deterministic_assets() -> None:
    d = json.loads((ROOT / "release/BUILD_DERIVATION.json").read_text()); assert "build each asset twice and require byte identity" in d["operations"]
def test_sd12_f41_02_normaliser_is_executable() -> None: assert callable(_module().normalise_sdist)
def test_sd12_f41_03_different_envelopes_normalise_identically(tmp_path: Path) -> None:
    a = tmp_path / "a.tar.gz"; b = tmp_path / "b.tar.gz"; _synthetic(a, mtime=1700000001); _synthetic(b, mtime=1700000099)
    module = _module(); module.normalise_sdist(a, epoch=1789689600); module.normalise_sdist(b, epoch=1789689600); assert a.read_bytes() == b.read_bytes()
def test_sd12_f41_04_normalised_payload_is_preserved(tmp_path: Path) -> None:
    p = tmp_path / "demo.tar.gz"; _synthetic(p, mtime=1700000001); _module().normalise_sdist(p, epoch=1789689600)
    with tarfile.open(p, "r:gz") as a:
        m = a.getmember("demo/file.txt"); assert m.mtime == 1789689600 and m.uid == m.gid == 0 and a.extractfile(m).read() == b"deterministic-sdist-test\n"
