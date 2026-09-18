PYTHON ?= python

.PHONY: test coverage build clean self-check

test:
	$(PYTHON) -m pytest -q

coverage:
	$(PYTHON) -m coverage erase
	$(PYTHON) -m coverage run -m pytest -q
	$(PYTHON) -m coverage report --fail-under=85

build:
	$(PYTHON) scripts/build_distributions.py

self-check:
	$(PYTHON) -m cdrse self-check --json

clean:
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov
