# PWA Forge

Turn any web app into a native-feeling Linux launcher. PWA Forge spins up isolated browser profiles, writes desktop files, and keeps external links under control on KDE Plasma, GNOME, and other XDG-friendly environments.

## Features

- Isolated Chromium-based profiles per app
- `.desktop` launchers, wrapper scripts, and icon management
- Smart external link routing with handler scripts and userscripts
- Registry, audit, and sync commands to keep installs tidy

## Requirements

- Linux desktop with XDG tooling (KDE Plasma, GNOME, etc.)
- Python 3.10+
- **Chromium-based browser**: Google Chrome, Chromium, or Microsoft Edge
  - *Note: Firefox is not supported for PWA creation (lacks app mode)*
- `xdg-utils` for desktop integration commands

## Installation

**Note:** PWA Forge is not yet published to PyPI. Install from source:

```bash
# Clone the repository
git clone https://github.com/bigr/pwa_forge.git
cd pwa_forge
pip install -e .

# Or install directly via pip with git
pip install git+https://github.com/bigr/pwa_forge.git
```

### Offline Installation

If you don't have internet access, you can run PWA Forge directly from the source directory:

```bash
# Extract the source code and add to PYTHONPATH
export PYTHONPATH="/path/to/pwa_forge/src:$PYTHONPATH"
python -m pwa_forge.cli --help
```

## Usage

### Basic PWA Creation

```bash
# Add a web app with isolated profile and desktop launcher
pwa-forge add https://notion.so --name "Notion" --browser chrome

# Add with custom ID and icon
pwa-forge add https://discord.com --name "Discord" --app-id discord --icon ~/discord-logo.png
```

### Management

```bash
# List all installed PWAs
pwa-forge list

# Edit PWA manifest (opens in $EDITOR)
pwa-forge edit notion

# Remove PWA and its data
pwa-forge remove notion --remove-profile --remove-icon
```

### External Link Handling

```bash
# Create handler for custom URLs (opens external links in system browser)
pwa-forge generate-handler --scheme ext --browser firefox
pwa-forge install-handler --scheme ext

# Generate userscript to rewrite external links
pwa-forge generate-userscript --scheme ext --in-scope-hosts notion.so
```

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

```bash
git clone https://github.com/bigr/pwa_forge.git
cd pwa_forge
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && pip install -e .

# Run tests and checks
make ci-local       # Recommended: simulate CI locally
make test          # Run unit tests with coverage
make help          # Show all available targets

# Install pre-commit hooks
pip install pre-commit && pre-commit install
```

## Documentation & Roadmap

- Full usage guide and examples: `docs/USAGE.md`
- Comprehensive testing documentation: `docs/TESTING.md`
- Specs and deep dives live in `docs/`
- Near-term focus: better Wayland support, icon fetching, backup/restore flows

## License

This project is licensed under the MIT License. See `LICENSE` for details.
