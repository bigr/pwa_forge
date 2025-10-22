# PWA Forge

Turn any web app into a native-feeling Linux launcher. PWA Forge spins up isolated browser profiles, writes desktop files, and keeps external links under control on KDE Plasma, GNOME, and other XDG-friendly environments.

## Features

- Isolated Chromium- or Firefox-based profiles per app
- `.desktop` launchers, wrapper scripts, and icon management
- Smart external link routing with handler scripts and userscripts
- Registry, audit, and sync commands to keep installs tidy

## Requirements

- Linux desktop with XDG tooling (KDE Plasma, GNOME, etc.)
- Python 3.10+
- One of: Google Chrome, Chromium, or Firefox
- `xdg-utils` for desktop integration commands

## Installation

```bash
pip install pwa-forge
```

From source:

```bash
git clone https://github.com/bigr/pwa_forge.git
cd pwa_forge
pip install -e .
```

## Quick Start

```bash
# Add a web app with its own profile and launcher
pwa-forge add https://example.com --name "Example App"

# Inspect installed PWAs
pwa-forge list

# Remove an app and its assets
pwa-forge remove example-app --remove-profile --remove-icon
```

## External Link Handling

```bash
# Create a firefox-backed handler for ff:// URLs
pwa-forge generate-handler --scheme ff --browser firefox

# Register it with XDG
pwa-forge install-handler --scheme ff

# Optional userscript to rewrite external links inside the PWA
pwa-forge generate-userscript --scheme ff --in-scope-hosts example.com
```

Clicks that leave the PWA are rewritten to the custom scheme and opened in the system browser.

## Configuration & Maintenance

```bash
# Inspect or tweak global settings
pwa-forge config list
pwa-forge config set default_browser chrome

# Manifests live under ~/.local/share/pwa-forge/apps/<id>/
pwa-forge edit <id>
pwa-forge sync <id>

# Audit installs or diagnose the host environment
pwa-forge audit <id>
pwa-forge audit --fix
pwa-forge doctor
```

## Development

Set up a development environment:

```bash
git clone https://github.com/bigr/pwa_forge.git
cd pwa_forge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

Run tests and checks:

```bash
pytest
pytest --cov=pwa_forge
ruff check pwa_forge tests
mypy pwa_forge
```

Install and run pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Documentation & Roadmap

- Specs and deep dives live in `docs/`
- Near-term focus: better Wayland support, icon fetching, backup/restore flows

## Continuous Integration

- **CI Pipeline**: GitHub Actions workflow at `.github/workflows/ci.yml` runs linting, type checks, and tests on pushes and pull requests targeting `main`.
- **Status Badge**: Add your repository badge once published, e.g. `![CI](https://github.com/<user>/pwa_forge/actions/workflows/ci.yml/badge.svg)`.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
