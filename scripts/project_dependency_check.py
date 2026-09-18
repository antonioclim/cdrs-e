#!/usr/bin/env python3
from __future__ import annotations

from importlib import metadata
from pathlib import Path
import json
import tomllib

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    rows = []
    failed = []
    for raw in project.get("dependencies", []):
        requirement = Requirement(raw)
        try:
            installed = metadata.version(requirement.name)
            ok = Version(installed) in requirement.specifier
        except metadata.PackageNotFoundError:
            installed = None
            ok = False
        row = {
            "requirement": raw,
            "name": requirement.name,
            "installed": installed,
            "satisfied": ok,
        }
        rows.append(row)
        if not ok:
            failed.append(row)
    result = {
        "status": "PASS" if not failed else "FAIL",
        "project": project["name"],
        "version": project["version"],
        "dependencies": rows,
        "failures": failed,
        "scope": "declared direct dependency lower-bound satisfaction in the active interpreter",
        "limitations": [
            "not a transitive or hashed lock verification",
            "not a vulnerability advisory scan",
            "not an independent dependency resolution",
        ],
    }
    (REPORTS / "project_dependency_check.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
