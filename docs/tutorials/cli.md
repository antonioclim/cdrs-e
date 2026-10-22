# CLI tutorial

```bash
cdrse version
cdrse validate-problem examples/forest_problem.json
cdrse solve-forest examples/forest_problem.json
cdrse solve-exhaustive examples/forest_problem.json --objective cut
cdrse dd examples/dsrg_witness_model.json 0
cdrse verify-certificate examples/valid_certificate.json
cdrse validate-protocol examples/frozen_protocol.json
cdrse self-check --json
```

Successful computational commands emit strict JSON. Expected argument, input
validation and file-access errors use exit status 2 and a JSON error on standard
error, without writing a successful result. `--help` is a separate human-readable
contract: help text on standard output and exit status 0. Unexpected internal
exceptions are not silently reclassified as input errors. The global
`--output PATH` option writes deterministic JSON to a file.
