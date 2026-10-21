#!/usr/bin/env python3
"""Historical rc1-envelope reassembly is unavailable for the local rc2 candidate.

The original source is preserved verbatim under
release/history/rc1_p7/scripts/reassemble_qualified_assets.py.
That archived script is historical evidence, not an rc2 build route.
"""
from __future__ import annotations

def main() -> int:
    raise RuntimeError("DEPENDENCY_BLOCKED: rc2 requires a fresh exact-backend build; historical rc1 envelope reassembly is prohibited")

if __name__ == "__main__":
    raise SystemExit(main())
