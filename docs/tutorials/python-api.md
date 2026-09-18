# Python API tutorial

The public API separates problem identity, arithmetic backends, solvers and certificates.

```python
import numpy as np
from cdrse import VARModel, coordinate_dd

model = VARModel(
    coefficients=(np.array([[0.0, 0.5], [0.5, 0.0]]),),
    innovation_covariance=np.eye(2),
)
value, diagnostics = coordinate_dd(model, (0,))
assert diagnostics.converged
```

For discrete problems, construct a `SelectionProblem` from validated JSON and call the solver matching the structural regime. Exact forest-cut output is not automatically exact DD output; attach the appropriate weak-coupling or cut-gap certificate before making a DD claim.

The package exposes three arithmetic semantics:

- `ExactRationalBackend` for directed cuts, modular resources and symbolic witnesses;
- `Float64Backend` for general numerical evaluation with residuals and condition diagnostics;
- `HighPrecisionAuditBackend` for small-instance audit, not production-scale optimisation.

A backend name is not sufficient evidence by itself. The result or certificate must state the actual error enclosure and exactness scope.
