"""Minimal deterministic CDRS-E forest example."""
from __future__ import annotations

from pathlib import Path
import json

from cdrse.algorithms import solve_forest_cut
from cdrse.models import SelectionProblem

payload = json.loads((Path(__file__).with_name("forest_problem.json")).read_text(encoding="utf-8"))
problem = SelectionProblem.from_dict(payload)
result = solve_forest_cut(problem)
print(json.dumps(result.to_dict(), indent=2, sort_keys=True, allow_nan=False))
