# DeltaCrown Makefile
# Quick commands for development and testing

.PHONY: help test obs-tests smoke synthetics-lint clean

help:
	@echo "DeltaCrown Development Commands"
	@echo "================================"
	@echo "make test            - Run all tests"
	@echo "make obs-tests       - Run observability tests only"
	@echo "make smoke           - Run smoke tests only"
	@echo "make synthetics-lint - Validate synthetics YAML"
	@echo "make clean           - Remove Python cache files"

test:
	pytest -v tests/

obs-tests:
	@echo "Running observability tests (Module 8.3)..."
	pytest -v -m observability tests/observability/

smoke:
	@echo "Running smoke tests (Phase 9)..."
	pytest -v -m smoke tests/smoke/

synthetics-lint:
	@echo "Validating synthetics YAML..."
	yamllint synthetics/uptime_checks.yml
	@python -c "import yaml; yaml.safe_load(open('synthetics/uptime_checks.yml')); print('✅ Synthetics YAML valid')"

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
