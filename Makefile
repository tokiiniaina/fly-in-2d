PYTHON ?= python3
MAP ?= maps/02_simple_fork.txt

.PHONY: install run cli debug test clean lint lint-strict

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) fly_in.py

cli:
	$(PYTHON) fly_in.py $(MAP)

debug:
	$(PYTHON) -m pdb fly_in.py $(MAP)

test:
	$(PYTHON) -m unittest discover -s tests -t .

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	$(PYTHON) -m flake8 flyin tests tools fly_in.py
	$(PYTHON) -m mypy flyin --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(PYTHON) -m flake8 flyin tests tools fly_in.py
	$(PYTHON) -m mypy flyin --strict
