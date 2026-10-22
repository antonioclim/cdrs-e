# QA2 installed-wheel provenance contract

The `clean_room_verify.py` compatibility filename now denotes an explicit
verification of an already installed wheel. It no longer creates virtual
environments, inherits host dependencies through a `.pth` file, installs an
sdist or invokes the unbounded numerical `self-check` command.

Provisioning and wheel installation remain separately authorised operations.
For an existing virtual environment with system-site-packages disabled, the
administrative API is:

```python
probe_installed_wheel(python, wheel, working_directory,
                      source_root=source_checkout, timeout_seconds=30)
```

The working directory must exist outside the source checkout. The helper uses
an allowlisted environment and `python -I -B`, compares every installed package
file with the wheel and binds the loaded `cdrse` module origins and hashes to
that same installed package. It requires a distinct virtual environment and
rejects editable installations and external site-packages on the probe path.
The result reports `PASS_INSTALLED_WHEEL_PROVENANCE_ONLY` and explicitly records
that numerical checks and sdist installation were not performed.

The CLI requires `--python`, `--wheel` and `--working-directory`; an optional
`--output` path is created exclusively and never overwrites an existing report.
This is a deliberate narrowing of the old implicit-installation interface.

These controls do not establish dependency hermeticity, independent-host
reproduction, global scientific correctness or G0 admission. Tests that mock a
probe response check reporting branches only; actual installed-module origin
checks, including cwd and PYTHONPATH traps, require their separate finite run.
SDist structure and literal source binding remain the responsibility of
`verify_distribution.py`. Neither helper grants execution authorisation.
