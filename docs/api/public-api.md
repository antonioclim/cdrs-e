# Public Python API

The supported top-level objects are:

```python
from cdrse import (
    VARModel,
    ServiceConstraints,
    SelectionProblem,
    DecisionCertificate,
    ExactRationalBackend,
    Float64Backend,
    HighPrecisionAuditBackend,
    coordinate_dd,
    projected_dd,
    directed_cut,
    dsrg_swap_witness,
)
```

Algorithm APIs live under `cdrse.algorithms`. The package follows semantic
versioning; however, `0.1.0rc1` is a release candidate and may change before
the first stable release.

## Result records and finite verification

The authoritative stored-cut result is `result.to_record()`; legacy numeric fields
are displays. `cdrse.verification.verify_solver_payload` independently enumerates
a small finite stored-cut model, with a default limit of 16 vertices. It verifies
the supported certificate contract and checks corresponding display fields.
Unenclosed callbacks remain uncertified. The function does not validate generic
DD numerical enclosures or population coverage.

Always pin the version and distribution digest recorded in the release manifest or other trusted delivery record. Apache-2.0 applies to the included software surface; repository visibility does not extend that licence to excluded manuscript, evidence or provenance material.

## Economic and robust helper boundary retained from qualified dev6

Economic scalar helpers use exact supplied integer/stored-binary64 operands and
one nearest finite binary64 display conversion. `supported_points` returns
extreme lower-hull representatives of a nondominated front, not all collinear or
duplicate supported labels. Finite scenario ranking uses exact aggregates before
display conversion, but callback results remain uncertified and the robust
reference route reports `exact=false` and `certified=false`. Explicit probability
vectors for CVaR remain unsupported. See the P10-SD4 contract.


## Exact and direct-Python boundary hardening in dev5

Exact-rational subsets use unique in-range integer indices, exact witness-domain checks remain rational and endpoint DD calls validate the same finite positive tolerance as non-endpoint calls. Direct Python models reject boolean numerical fields and textual numerical arrays. Canonical hashing requires textual mapping keys. These checks validate representation and domain consistency only.
