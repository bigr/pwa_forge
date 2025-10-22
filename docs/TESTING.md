# Testing Guide

## Quick Start

```bash
# Run all tests (excluding Playwright tests by default)
pytest -m "not playwright"

# Run tests with coverage
pytest --cov=pwa_forge --cov-report=html -m "not playwright"

# Run specific test file
pytest tests/unit/test_paths.py

# Run specific test
pytest tests/unit/test_paths.py::TestExpandPath::test_expand_home_directory

# Run Playwright browser integration tests (requires Playwright installation)
pytest tests/playwright -v
```

## Using Make for Common Tasks

We provide a `Makefile` with convenient targets for testing and development:

```bash
# Show all available targets
make help

# Install development dependencies
make install-dev

# Install Playwright and browsers
make install-playwright

# Run unit tests with coverage (fast)
make test

# Run Playwright tests
make test-playwright

# Run all tests including Playwright
make test-all

# Simulate CI pipeline locally (recommended before pushing)
make ci-local

# Run linting
make lint

# Format code
make format

# Generate HTML coverage report
make coverage
```

The `make ci-local` target is especially useful to catch issues before pushing to GitHub.

## Multi-Version Testing with Tox

To test across multiple Python versions (3.10, 3.11, 3.12, 3.13):

```bash
# Install tox
pip install tox

# Run tests on all available Python versions
tox

# Run tests on specific Python version
tox -e py312

# Run only linting (ruff + mypy)
tox -e lint

# Run code formatting
tox -e format

# Run Playwright browser integration tests
tox -e playwright

# Run all tests (unit + Playwright) with combined coverage
tox -e coverage-all
```

### Installing Multiple Python Versions

**On Ubuntu/Debian:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3.11 python3.12 python3.13
```

**On Fedora:**
```bash
sudo dnf install python3.10 python3.11 python3.12 python3.13
```

**Using pyenv (recommended for development):**
```bash
# Install pyenv
curl https://pyenv.run | bash

# Install Python versions
pyenv install 3.10.14
pyenv install 3.11.9
pyenv install 3.12.5
pyenv install 3.13.0

# Make them available to tox
pyenv global 3.13.0 3.12.5 3.11.9 3.10.14
```

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

```bash
# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run specific hook
pre-commit run mypy --all-files
```

The hooks include:
- **ruff** - Linting and auto-fixes
- **ruff-format** - Code formatting
- **mypy** - Type checking (catches Python 3.12 compatibility issues)
- **trailing-whitespace** - Remove trailing whitespace
- **end-of-file-fixer** - Ensure files end with newline
- **check-added-large-files** - Prevent large files from being committed

## Type Checking

```bash
# Check types with mypy
mypy src

# Check specific file
mypy src/pwa_forge/cli.py
```

## Code Quality

```bash
# Lint with ruff
ruff check src tests

# Auto-fix issues
ruff check --fix src tests

# Format code
ruff format src tests
```

## Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=pwa_forge --cov-report=html

# Open in browser
xdg-open htmlcov/index.html

# Generate terminal report with missing lines
pytest --cov=pwa_forge --cov-report=term-missing
```

## Browser Integration Testing with Playwright

PWA Forge includes browser integration tests to verify userscript functionality and URL handler integration.

### Prerequisites

```bash
# Install Playwright dependencies
pip install .[playwright]

# Install Playwright browsers (Chromium, Firefox, WebKit)
python -m playwright install

# Or install only Chromium (recommended for CI)
python -m playwright install chromium

# Install system dependencies (Linux only)
python -m playwright install --with-deps chromium
```

### Running Playwright Tests

```bash
# Run all Playwright tests (headless Chromium - default)
pytest tests/playwright -v --browser chromium

# Run with specific browser
pytest tests/playwright --browser firefox
pytest tests/playwright --browser webkit

# Run in headed mode (visible browser window)
pytest tests/playwright --headed --browser chromium

# Run specific test file
pytest tests/playwright/test_userscript_link_rewrite.py -v

# Use tox environment (automatically installs browsers)
tox -e playwright
```

**Important**: The `--headed` flag is a boolean flag (no value needed). Do NOT use `--headed=false` or `--headed=true` - this will cause an error. Omit the flag for headless mode (default).

### What Playwright Tests Verify

The browser integration tests verify:

1. **External Link Rewriting**
   - Links to external domains are rewritten to custom scheme (e.g., `testff:`)
   - Internal/same-site links remain unchanged
   - `mailto:` and `tel:` links are preserved
   - Dynamically added links are handled via MutationObserver

2. **window.open() Patching**
   - `window.open()` calls with external URLs use custom scheme
   - Internal URLs passed to `window.open()` remain unchanged

3. **Handler Script Integration**
   - Handler scripts decode encoded URLs correctly
   - Complex URLs with query parameters and fragments are handled
   - Non-HTTP/HTTPS URLs are rejected for security
   - Empty or invalid input is rejected gracefully

### Coverage for Playwright Tests

Playwright tests can be included in coverage reports:

```bash
# Run Playwright tests with coverage
pytest tests/playwright --cov=pwa_forge --cov-report=term-missing

# Run all tests (unit + Playwright) with combined coverage
tox -e coverage-all

# Or using Make
make test-all  # Includes coverage for all tests
```

Coverage tracking for Playwright tests verifies that our userscript templates and handler script templates are properly exercised during browser integration testing.

### Skipping Playwright Tests

Playwright tests are marked with `@pytest.mark.playwright` and can be skipped:

```bash
# Run all tests EXCEPT Playwright tests
pytest -m "not playwright"

# Or use the convenience Make target
make test
```

### CI Integration

GitHub Actions runs Playwright tests on:
- Python 3.12
- Ubuntu Latest
- Chromium browser (headless)

Artifacts (screenshots, traces) are uploaded on test failures.

## Continuous Integration

GitHub Actions runs tests on:
- **Unit/Integration Tests**: Python 3.10, 3.11, 3.12 (Ubuntu Latest)
- **Playwright Tests**: Python 3.12, Chromium (Ubuntu Latest)
- **Linting**: Python 3.12 (pre-commit hooks, mypy)

See `.github/workflows/ci.yml` for CI configuration.

## Writing Tests

### Test Structure

```
tests/
├── unit/           # Unit tests for individual modules
│   ├── test_paths.py
│   ├── test_config.py
│   └── ...
├── integration/    # Integration tests (future)
└── fixtures/       # Test data (future)
```

### Test Naming Conventions

- Test files: `test_<module>.py`
- Test classes: `Test<Feature>`
- Test functions: `test_<what_it_tests>`

### Example Test

```python
"""Unit tests for my module."""

from __future__ import annotations

import pytest
from pwa_forge import my_module


class TestMyFeature:
    """Test MyFeature functionality."""

    def test_basic_case(self) -> None:
        """Test the basic use case."""
        result = my_module.my_function("input")
        assert result == "expected output"

    def test_edge_case(self) -> None:
        """Test edge case behavior."""
        with pytest.raises(ValueError):
            my_module.my_function(None)
```

## Troubleshooting

### Tox can't find Python version

```bash
# Check available Python versions
tox --showconfig

# Skip missing interpreters
tox --skip-missing-interpreters
```

### Pre-commit hook fails

```bash
# Update hooks to latest versions
pre-commit autoupdate

# Clear cache and re-run
pre-commit clean
pre-commit run --all-files
```

### Mypy cache issues

```bash
# Clear mypy cache
rm -rf .mypy_cache
mypy src
```
