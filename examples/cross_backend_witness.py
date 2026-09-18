"""Cross-check the exact, float64 and high-precision DSRG witness."""
from __future__ import annotations

import json
import numpy as np

from cdrse.backends import ExactRationalBackend, HighPrecisionAuditBackend
from cdrse.models import VARModel
from cdrse.objectives import dsrg_swap_witness

model = VARModel(
    coefficients=(np.array([[0.0, 0.5], [0.5, 0.0]]),),
    innovation_covariance=np.eye(2),
)
exact = ExactRationalBackend.dsrg_swap_witness("1/2")
float64 = dsrg_swap_witness(0.5)
high_precision, audit = HighPrecisionAuditBackend(decimal_digits=50, tolerance="1e-38").projected_var_dd(
    model, np.array([[1.0], [0.0]])
)
print(
    json.dumps(
        {
            "exact_expression": str(exact),
            "float64": float64,
            "high_precision": str(high_precision),
            "audit": audit,
        },
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
)
