# Testing Guide

## Quick Start

```bash
# Run tests with current Python version
pytest

# Run tests with coverage
pytest --cov=pwa_forge --cov-report=html

# Run specific test file
pytest tests/unit/test_paths.py

# Run specific test
pytest tests/unit/test_paths.py::TestExpandPath::test_expand_home_directory
```

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

## Continuous Integration

GitHub Actions runs tests on:
- Python 3.10, 3.11, 3.12, 3.13
- Ubuntu Latest

See `.github/workflows/test.yml` for CI configuration.

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
