#!/usr/bin/env python3
# HISTORICAL GENERATOR: figures describe the Phase XLII private candidate and are retained for provenance only.
from __future__ import annotations

from pathlib import Path
import csv
import json

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def save(fig, name: str) -> None:
    for suffix in ("png", "pdf", "svg"):
        kwargs = {"dpi": 240} if suffix == "png" else {}
        fig.savefig(OUT / f"{name}.{suffix}", bbox_inches="tight", pad_inches=0.08, **kwargs)
    plt.close(fig)


# Figure 1 — architecture.
fig, ax = plt.subplots(figsize=(11, 7))
ax.set_xlim(0, 12)
ax.set_ylim(0, 9)
ax.axis("off")
ax.text(6, 8.55, "CDRS-E companion software architecture", ha="center", fontsize=16, fontweight="bold")
boxes = [
    (1.6, 6.8, 2.7, 1.05, "Models and identity", "VAR, constraints, hashes"),
    (4.65, 6.8, 2.7, 1.05, "Objectives and economics", "DD, cut, risk, Pareto"),
    (7.7, 6.8, 2.7, 1.05, "Arithmetic backends", "exact, float64, audit"),
    (10.5, 6.8, 2.0, 1.05, "Schemas", "problem, result, protocol"),
    (2.2, 4.3, 3.2, 1.15, "Certified algorithms", "forest, treewidth, B&B, dynamic"),
    (6.0, 4.3, 3.2, 1.15, "Certificates", "algorithmic, numeric, statistical, economic"),
    (9.8, 4.3, 3.2, 1.15, "Interfaces", "typed API, CLI, JSON reports"),
    (3.8, 1.75, 3.4, 1.15, "Assurance", "unit/property/regression tests, coverage"),
    (8.2, 1.75, 3.4, 1.15, "Distribution", "wheel, sdist, clean-room install"),
]
for x, y, w, h, title, subtitle in boxes:
    patch = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.035", facecolor="white", linewidth=1.2)
    ax.add_patch(patch)
    ax.text(x, y+0.18, title, ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(x, y-0.2, subtitle, ha="center", va="center", fontsize=8.5)
for start, end in [
    ((1.6, 6.25), (2.2, 4.9)), ((4.65, 6.25), (2.2, 4.9)), ((7.7, 6.25), (6.0, 4.9)),
    ((10.5, 6.25), (9.8, 4.9)), ((2.2, 3.72), (3.8, 2.35)), ((6.0, 3.72), (3.8, 2.35)),
    ((9.8, 3.72), (8.2, 2.35)), ((6.0, 3.72), (8.2, 2.35)),
]:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, linewidth=1.0))
ax.text(6, 0.55, "Public release gates remain closed: no licence, repository URL, DOI, PyPI upload or Zenodo deposit is asserted.", ha="center", fontsize=9.5)
save(fig, "Figure_1_software_architecture")

# Figure 2 — assurance pipeline.
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.set_xlim(0, 12)
ax.set_ylim(0, 6)
ax.axis("off")
ax.text(6, 5.45, "Phase XLII assurance and delivery pipeline", ha="center", fontsize=16, fontweight="bold")
stages = [
    (1.0, "Source", "src-layout\ntyped package"),
    (3.0, "Test", "54 tests\n89% branch-aware"),
    (5.0, "Audit", "AST type/security\nmetadata gates"),
    (7.0, "Build", "wheel + sdist\nCRC/path checks"),
    (9.0, "Install", "fresh venvs\nwheel + sdist"),
    (11.0, "Seal", "manifest\nclean extraction"),
]
for x, title, sub in stages:
    p = FancyBboxPatch((x-.72, 2.35), 1.44, 1.55, boxstyle="round,pad=.035", facecolor="white", linewidth=1.2)
    ax.add_patch(p); ax.text(x, 3.48, title, ha="center", fontsize=10, fontweight="bold"); ax.text(x, 2.83, sub, ha="center", fontsize=8.5)
for (x1, *_), (x2, *__) in zip(stages[:-1], stages[1:]):
    ax.add_patch(FancyArrowPatch((x1+.72, 3.12), (x2-.72, 3.12), arrowstyle="-|>", mutation_scale=12, linewidth=1.0))
ax.text(6, 1.35, "Every linked artefact must exist, hash correctly and pass the package verifier after independent extraction.", ha="center", fontsize=9.5)
ax.text(6, 0.75, "Optional Ruff/mypy and container execution are recorded as unavailable environment gates, not silently claimed as passed.", ha="center", fontsize=9)
save(fig, "Figure_2_assurance_pipeline")

# Figure 3 — coverage by module.
coverage = json.loads((ROOT / "reports" / "coverage.json").read_text(encoding="utf-8"))
rows = []
for path, data in coverage["files"].items():
    if path.endswith("/__init__.py") or path.endswith("/_version.py") or path.endswith("/__main__.py"):
        continue
    name = path.replace("src/cdrse/", "")
    rows.append((name, data["summary"]["percent_covered"]))
rows.sort(key=lambda x: (x[1], x[0]))
with (ROOT / "reports" / "figures" / "Figure_3_coverage_by_module.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream); writer.writerow(["module", "coverage_percent"]); writer.writerows(rows)
fig, ax = plt.subplots(figsize=(10, 7.5))
ax.barh([r[0] for r in rows], [r[1] for r in rows])
ax.axvline(85, linestyle="--", linewidth=1)
ax.set_xlim(0, 100)
ax.set_xlabel("Branch-aware coverage (%)")
ax.set_title("Coverage by implementation module")
ax.grid(axis="x", alpha=0.25)
fig.tight_layout()
save(fig, "Figure_3_coverage_by_module")

# Figure 4 — FAIR4RS status counts.
with (ROOT / "reports" / "FAIR4RS_MATRIX.csv").open(encoding="utf-8") as stream:
    fair = list(csv.DictReader(stream))
order = ["PASS", "PASS_PRIVATE", "LOCAL_PASS", "PARTIAL_PASS", "PARTIAL", "OPEN", "BLOCKED", "NOT_APPLICABLE", "NOT_YET_APPLICABLE"]
counts = {status: sum(row["status"] == status for row in fair) for status in order}
counts = {k: v for k, v in counts.items() if v}
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.bar(list(counts), list(counts.values()))
ax.set_ylabel("Number of FAIR4RS principles")
ax.set_title("Private-candidate FAIR4RS readiness")
ax.tick_params(axis="x", rotation=35)
ax.grid(axis="y", alpha=0.25)
for i, value in enumerate(counts.values()):
    ax.text(i, value + 0.08, str(value), ha="center", fontsize=9)
fig.tight_layout()
save(fig, "Figure_4_fair4rs_readiness")

print(f"generated {len(list(OUT.glob('*.png')))} report figures")
