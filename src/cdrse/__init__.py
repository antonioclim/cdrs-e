"""CDRS-E auditable research software release candidate."""

from ._version import __version__
from .backends import ExactRationalBackend, Float64Backend, HighPrecisionAuditBackend
from .certificates import DecisionCertificate
from .models import SelectionProblem, ServiceConstraints, VARModel
from .objectives import coordinate_dd, directed_cut, dsrg_swap_witness, projected_dd

__all__ = [
    "__version__",
    "VARModel",
    "ServiceConstraints",
    "SelectionProblem",
    "DecisionCertificate",
    "ExactRationalBackend",
    "Float64Backend",
    "HighPrecisionAuditBackend",
    "coordinate_dd",
    "projected_dd",
    "directed_cut",
    "dsrg_swap_witness",
]
