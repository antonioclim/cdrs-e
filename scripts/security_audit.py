#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TARGETS = [ROOT / "src", ROOT / "scripts"]
FORBIDDEN_CALLS = {"eval", "exec", "compile", "pickle.loads", "yaml.load", "subprocess.Popen", "os.system"}

# Exact prepared administrative driver only; a byte change requires fresh review.
# This does not permit arbitrary subprocess use or prove process containment.
REVIEWED_PROCESS_DRIVER = ("scripts/run_rc3_release_validation.py", "27614f780affa57719365a62dc8eed58ef4edfea33364f24dd97d561b1c27695")


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{dotted(node.value)}.{node.attr}".strip(".")
    return ""


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    findings = []
    reviewed_exceptions = []
    files = 0
    for root in TARGETS:
        for path in sorted(root.rglob("*.py")):
            files += 1
            payload = path.read_bytes()
            relative = str(path.relative_to(ROOT))
            tree = ast.parse(payload.decode("utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = dotted(node.func)
                    if name in FORBIDDEN_CALLS:
                        finding = {"file": relative, "line": node.lineno, "call": name}
                        if name == "subprocess.Popen" and (relative, hashlib.sha256(payload).hexdigest()) == REVIEWED_PROCESS_DRIVER:
                            reviewed_exceptions.append({**finding, "sha256": REVIEWED_PROCESS_DRIVER[1], "scope": "exact reviewed POSIX administrative release-driver bytes; current execution remains UNRUN"})
                        else:
                            findings.append(finding)
    result = {
        "status": "PASS" if not findings else "FAIL",
        "python_files": files,
        "forbidden_calls": findings,
        "exact_reviewed_call_exceptions": reviewed_exceptions,
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
