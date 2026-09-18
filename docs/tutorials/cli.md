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

All commands emit strict JSON. Failures use exit status 2 and a JSON error on
standard error. The global `--output PATH` option writes deterministic JSON to a
file.
