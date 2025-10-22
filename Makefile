.PHONY: help test test-unit test-playwright test-all lint format pre-commit ci-local install-dev install-playwright

# Use virtual environment if it exists
VENV := .venv
ifeq ($(shell test -d $(VENV) && echo 1),1)
	PYTHON := $(VENV)/bin/python
	PYTEST := $(VENV)/bin/pytest
	RUFF := $(VENV)/bin/ruff
	MYPY := $(VENV)/bin/mypy
	PRECOMMIT := $(VENV)/bin/pre-commit
else
	PYTHON := python
	PYTEST := pytest
	RUFF := ruff
	MYPY := mypy
	PRECOMMIT := pre-commit
endif

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-dev:  ## Install development dependencies
	pip install -e .[dev]
	pre-commit install

install-playwright:  ## Install Playwright and browsers
	pip install -e .[playwright]
	$(PYTHON) -m playwright install --with-deps chromium

test-unit:  ## Run unit and integration tests (fast)
	$(PYTEST) -q -m "not playwright"

test-playwright:  ## Run Playwright browser integration tests
	$(PYTEST) tests/playwright -v --browser chromium

test-all:  ## Run all tests including Playwright
	$(PYTEST) -v

test:  ## Run unit tests with coverage (default)
	$(PYTEST) -q --cov=pwa_forge --cov-report=term-missing -m "not playwright"

lint:  ## Run linting (ruff + mypy)
	$(RUFF) check src tests
	$(MYPY) src

format:  ## Format code with ruff
	$(RUFF) format src tests

pre-commit:  ## Run all pre-commit hooks
	$(PRECOMMIT) run --all-files

ci-local:  ## Simulate CI pipeline locally
	@echo "==> Running linting..."
	@$(RUFF) check src tests
	@echo ""
	@echo "==> Running type checks..."
	@$(MYPY) src
	@echo ""
	@echo "==> Running unit tests..."
	@$(PYTEST) -q -m "not playwright"
	@echo ""
	@echo "==> Running Playwright tests..."
	@if $(PYTHON) -c "import playwright" 2>/dev/null; then \
		$(PYTEST) tests/playwright -v --browser chromium; \
	else \
		echo "Playwright not installed. Install with: make install-playwright"; \
		echo "Skipping Playwright tests."; \
	fi
	@echo ""
	@echo "✅ All CI checks passed locally!"

coverage:  ## Generate HTML coverage report
	$(PYTEST) --cov=pwa_forge --cov-report=html -m "not playwright"
	@echo "Coverage report: htmlcov/index.html"

clean:  ## Clean build artifacts and caches
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache .tox .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
