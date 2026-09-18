#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import ast
import json

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TARGETS = [ROOT / "src", ROOT / "scripts"]
FORBIDDEN_CALLS = {"eval", "exec", "compile", "pickle.loads", "yaml.load", "subprocess.Popen", "os.system"}


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{dotted(node.value)}.{node.attr}".strip(".")
    return ""


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    findings = []
    files = 0
    for root in TARGETS:
        for path in sorted(root.rglob("*.py")):
            files += 1
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = dotted(node.func)
                    if name in FORBIDDEN_CALLS:
                        findings.append({"file": str(path.relative_to(ROOT)), "line": node.lineno, "call": name})
    result = {
        "status": "PASS" if not findings else "FAIL",
        "python_files": files,
        "forbidden_calls": findings,
        "scope": "finite exact-name AST call scan over src/ and scripts/",
        "limitations": [
            "no alias or data-flow analysis",
            "no dependency advisory scan",
            "no filesystem, archive, CI or container policy proof",
            "PASS is not an exhaustive security-audit verdict",
        ],
    }
    (REPORTS / "security_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
