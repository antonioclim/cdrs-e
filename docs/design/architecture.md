# Software architecture

The package uses a `src/` layout and a small dependency surface. Scientific
objects are immutable dataclasses. JSON identity is computed from canonical
serialisation. Algorithms return typed result objects rather than free-form
prints.

```text
cdrse/
  models.py          validated VAR and service-feasibility objects
  objectives.py      DD, projected innovations, cuts and weak-coupling bounds
  backends.py        exact-rational, float64 and high-precision audit semantics
  economics.py       cost ledgers, risk aggregation and Pareto operations
  certificates.py    four-layer decision certificates
  protocols.py       frozen-protocol identity
  algorithms/        exact, anytime, dynamic and Grassmann reference solvers
  schema_files/      JSON Schemas shipped in the wheel
  cli.py              stable command-line entry point
```

Phase XLII deliberately avoids a plug-in system. The backend boundary is kept
explicit until Phase XLIV supplies evidence that extensibility is needed.
