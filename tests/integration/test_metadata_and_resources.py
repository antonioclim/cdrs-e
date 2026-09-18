from __future__ import annotations

from importlib import resources
from pathlib import Path
import json
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_static_identity() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    project = data["project"]
    assert project["name"] == "cdrs-e"
    assert project["version"] == "0.1.0rc1"
    assert project["authors"] == [{"name": "Antonio Clim", "email": "Antonio.clim@csie.ase.ro"}]
    assert project["license"] == "Apache-2.0"
    assert project["license-files"] == ["LICENSE", "NOTICE"]
    assert project["scripts"]["cdrse"] == "cdrse.cli:main"


def test_release_gates_are_explicit() -> None:
    text = " ".join((ROOT / "PUBLIC_RELEASE_LICENCE_GATE.md").read_text().split())
    assert "Apache License 2.0 has been" in text
    codemeta = json.loads((ROOT / "codemeta.json").read_text())
    assert codemeta["license"] == "https://spdx.org/licenses/Apache-2.0"
    assert codemeta["codeRepository"] == "https://github.com/antonioclim/cdrs-e"


def test_packaged_schema_resources_exist() -> None:
    directory = resources.files("cdrse.schema_files")
    for name in ("problem.schema.json", "certificate.schema.json", "protocol.schema.json", "result.schema.json"):
        assert directory.joinpath(name).is_file()
