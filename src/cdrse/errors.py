"""Domain-specific exceptions used by the public API."""


class CDRSError(Exception):
    """Base exception for CDRS-E software errors."""


class ValidationError(CDRSError, ValueError):
    """Raised when a problem, model or certificate violates its contract."""


class NumericalConvergenceError(CDRSError, RuntimeError):
    """Raised when a numerical backend fails its declared convergence gate."""


class UnsupportedBackendError(CDRSError, NotImplementedError):
    """Raised when a backend does not support a requested operation."""
