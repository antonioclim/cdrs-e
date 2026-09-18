#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import ast
import json

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SRC = ROOT / "src" / "cdrse"


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    missing = []
    public_functions = 0
    for path in sorted(SRC.rglob("*.py")):
        if path.name.startswith("_") or "schema_files" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                public_functions += 1
                arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                if any(argument.annotation is None for argument in arguments if argument.arg not in {"self", "cls"}):
                    missing.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.name}:argument")
                if node.returns is None:
                    missing.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.name}:return")
    result = {
        "status": "PASS" if not missing else "FAIL",
        "public_functions": public_functions,
        "missing_annotations": missing,
        "scope": "top-level public function syntax only",
        "limitations": ["class methods, overload semantics and static type-checker soundness are not evaluated"],
    }
    (REPORTS / "type_contract_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
