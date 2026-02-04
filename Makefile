# DeltaCrown Test Makefile
# Simple targets for running tests with dockerized PostgreSQL

.PHONY: help test test-quick test-phase11 test-admin docker-up docker-down docker-clean

help:
	@echo "DeltaCrown Test Targets:"
	@echo ""
	@echo "  make test          - Run all tests with Docker DB"
	@echo "  make test-quick    - Run tests without rebuilding Docker"
	@echo "  make test-phase11  - Run Phase 11 regression tests only"
	@echo "  make test-admin    - Run admin stability tests only"
	@echo "  make docker-up     - Start test database container"
	@echo "  make docker-down   - Stop test database container"
	@echo "  make docker-clean  - Remove test database volume (reset DB)"
	@echo ""

test:
	@powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1

test-quick:
	@powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -NoBuild

test-phase11:
	@powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 tests/test_team_creation_regression.py

test-admin:
	@powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 tests/test_team_creation_regression.py::TestAdminStability

docker-up:
	@cd ops && docker-compose -f docker-compose.test.yml up -d
	@echo "Test database started on localhost:54329"

docker-down:
	@cd ops && docker-compose -f docker-compose.test.yml down
	@echo "Test database stopped"

docker-clean:
	@cd ops && docker-compose -f docker-compose.test.yml down -v
	@echo "Test database volume removed"
