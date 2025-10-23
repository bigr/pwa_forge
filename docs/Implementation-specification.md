# Implementation Specification: PWA Forge

## Implementation Status Summary (2025-10-23)

**Completed Phases (Phases 1-7):** ✅
- ✅ Phase 1: Core Infrastructure (logging, config, templates, paths)
- ✅ Phase 2: Basic PWA Management (add, list, remove commands)
- ✅ Phase 3: Browser Integration Test Framework (Playwright tests)
- ✅ Phase 4: URL Handler System (generate-handler, install-handler, generate-userscript)
- ✅ Phase 5: Validation & Audit (audit, sync, edit commands)
- ✅ Phase 6: Testing & Polish (E2E tests, documentation, 74% coverage)
- ✅ Phase 7: Release Preparation & Polish (config commands, doctor command, shell completion)

**Current Status:**
- **Test Coverage:** 78% (381 tests: 252 unit, 40 integration, 24 E2E, 65 Playwright browser tests)
- **CI/CD:** GitHub Actions with linting, type checking, and multi-Python testing
- **Code Quality:** Pre-commit hooks, mypy strict typing, ruff linting
- **Documentation:** README, TESTING.md, USAGE.md, TROUBLESHOOTING.md complete
- **Commands:** 14 commands implemented
  - ✅ **Fully working:** add, list, remove, audit, sync, edit, generate-handler, install-handler, generate-userscript, version, doctor, completion
  - ✅ **Config management:** config get, config set, config list, config reset, config edit

**Remaining Work (Optional/Future):**

**Low Priority (Future Enhancement):**
- Error code standardization (currently using exit codes 0/1)
- Release process automation (CHANGELOG.md, git tag, PyPI publishing)
- System packaging (apt/deb, flatpak, snap, AUR) - see Packaging section below

**Project Status:** ✅ **FEATURE COMPLETE**

All core functionality has been implemented and tested. The tool is ready for use and can manage PWAs,
URL handlers, userscripts, configuration, and system diagnostics. Shell completion is available for
bash, zsh, and fish.

---

## Project Overview

**pwa-forge** is a Python-based CLI tool for managing Progressive Web Apps (PWAs) as standalone applications on Linux desktop environments (primarily KDE/Plasma, with GNOME compatibility). The tool automates the creation of isolated browser instances with custom launchers, handles external link redirection to system browsers, and provides comprehensive PWA lifecycle management.

## Core Objectives

1. Create isolated PWA instances with separate browser profiles
2. Generate `.desktop` launcher files with proper configuration
3. Implement external link redirection to system default browser
4. Manage custom URL scheme handlers
5. Provide audit and lifecycle management capabilities

## Functional Requirements

### 1. PWA Management Commands

#### `pwa-forge add <url>`
Creates a new PWA instance.

**Required Parameters:**
- `<url>` - The web application URL

**Optional Parameters:**
- `--name NAME` - Display name for the application (default: extracted from URL)
- `--id ID` - Unique identifier (default: generated from name)
- `--browser {chrome,chromium,firefox,edge}` - Browser engine to use (default: chrome)
- `--profile DIR` - Custom profile directory (default: `~/.config/pwa-forge/apps/<id>`)
- `--icon PATH` - Path to application icon (default: attempts to fetch from web)
- `--out-of-scope {open-in-default,same-browser-window,same-browser-new-window}` - Behavior for external links (default: open-in-default)
- `--inject-userscript PATH` - Path to custom userscript for link interception
- `--wm-class NAME` - Custom StartupWMClass for window manager integration
- `--chrome-flags FLAGS` - Additional Chrome/Chromium flags
- `--dry-run` - Show what would be created without making changes

**Behavior:**
- Validates URL accessibility
- Creates isolated browser profile directory
- Generates wrapper script in `~/.local/bin/pwa-forge-wrappers/<id>`
- Creates `.desktop` file in `~/.local/share/applications/pwa-forge-<id>.desktop`
- Copies/downloads icon to `~/.local/share/icons/pwa-forge/<id>.{svg,png}`
- Creates manifest file at `~/.local/share/pwa-forge/apps/<id>/manifest.yaml`
- If `--inject-userscript` is specified, installs userscript and provides activation instructions
- Updates registry index at `~/.local/share/pwa-forge/registry.json`
- Runs `update-desktop-database` to register the application

#### `pwa-forge list`
Lists all managed PWA instances.

**Optional Parameters:**
- `--verbose` - Show detailed information including profile paths, flags, and configuration
- `--format {table,json,yaml}` - Output format (default: table)

**Output Fields:**
- ID
- Name
- URL
- Browser
- Status (active/broken)
- Out-of-scope behavior

#### `pwa-forge remove <id>`
Removes a PWA instance.

**Required Parameters:**
- `<id>` - Application ID or name

**Optional Parameters:**
- `--remove-profile` - Also delete the browser profile directory
- `--remove-icon` - Also delete the icon file
- `--keep-userdata` - Keep browser profile but remove launcher
- `--dry-run` - Show what would be removed without making changes

**Behavior:**
- Removes `.desktop` file
- Removes wrapper script
- Optionally removes profile directory and icon
- Updates registry index
- Runs `update-desktop-database`

#### `pwa-forge audit <id>`
Validates PWA configuration and functionality.

**Required Parameters:**
- `<id>` - Application ID or name (omit to audit all)

**Optional Parameters:**
- `--open-test-page` - Launch PWA with test page to verify link handling
- `--fix` - Attempt to repair broken configurations

**Checks Performed:**
- `.desktop` file exists and is valid
- Wrapper script exists and is executable
- Profile directory exists
- Icon file exists
- StartupWMClass matches configuration
- Browser executable is available
- Custom URL scheme handler is registered (if applicable)
- Userscript is present (if configured)

**Output:**
- PASS/FAIL status for each check
- Detailed error messages for failures
- Suggestions for fixes

#### `pwa-forge edit <id>`
Opens the manifest file in `$EDITOR` for manual editing.

**Post-edit Behavior:**
- Validates YAML syntax
- Offers to regenerate artifacts (`sync`)

#### `pwa-forge sync <id>`
Regenerates all artifacts from the manifest file.

**Use Cases:**
- After manual manifest editing
- To update wrapper scripts with new flags
- To regenerate desktop files with updated metadata

### 2. URL Scheme Handler Management

#### `pwa-forge generate-handler`
Generates a URL scheme handler script.

**Required Parameters:**
- `--scheme SCHEME` - URL scheme to handle (e.g., "ff" for ff:// URLs)

**Optional Parameters:**
- `--browser {firefox,chrome,chromium}` - Browser to open URLs in (default: firefox)
- `--out PATH` - Output path for handler script (default: `~/.local/bin/pwa-forge-handler-<scheme>`)
- `--system` - Install system-wide in `/usr/local/bin` (requires sudo)

**Generated Script Behavior:**
- Receives URLs in format `<scheme>:<encoded-url>`
- Decodes URL-encoded payload
- Validates URL is http/https
- Launches specified browser with decoded URL
- Logs activity for debugging

#### `pwa-forge install-handler`
Registers a URL scheme handler with the system.

**Required Parameters:**
- `--scheme SCHEME` - URL scheme to register

**Optional Parameters:**
- `--handler-script PATH` - Path to handler script (default: auto-generated)
- `--system` - Install system-wide (requires sudo)

**Behavior:**
- Creates `.desktop` file for the handler
- Registers via `xdg-mime default <desktop-file> x-scheme-handler/<scheme>`
- Updates desktop database
- Verifies registration with `xdg-mime query default x-scheme-handler/<scheme>`

### 3. Userscript Generation

#### `pwa-forge generate-userscript`
Generates a userscript for external link interception.

**Optional Parameters:**
- `--scheme SCHEME` - URL scheme to redirect to (default: ff)
- `--in-scope-hosts HOSTS` - Comma-separated list of hosts to keep in-app
- `--out PATH` - Output path for userscript

**Generated Userscript Features:**
- Intercepts clicks on `<a>` elements
- Patches `window.open()` calls
- Monitors dynamically added links via MutationObserver
- Redirects external URLs to custom scheme
- Preserves internal navigation

### 4. Configuration Management

#### `pwa-forge config`
Manages global configuration.

**Subcommands:**
- `get KEY` - Display configuration value
- `set KEY VALUE` - Set configuration value
- `list` - Show all configuration
- `reset` - Reset to defaults
- `edit` - Open config file in `$EDITOR`

**Configuration File Location:**
- User mode: `~/.config/pwa-forge/config.yaml`
- System mode: `/etc/pwa-forge/config.yaml`

### 5. Utility Commands

#### `pwa-forge template`
Displays or exports file templates.

**Required Parameters:**
- `--type {desktop,wrapper,userscript,handler,manifest}` - Template type

**Optional Parameters:**
- `--out PATH` - Export to file instead of stdout
- `--format {template,filled}` - Show template variables or example filled version

#### `pwa-forge scaffold <id>`
Creates a skeleton manifest and directory structure for manual configuration.

#### `pwa-forge doctor`
Diagnoses system configuration and dependencies.

**Checks:**
- Browser executables availability
- XDG utilities presence
- Directory permissions
- Desktop environment detection
- Python dependencies

## Configuration File Formats

### Global Configuration (`config.yaml`)

```yaml
# Default browser for PWAs
default_browser: chrome

# Browser executables
browsers:
  chrome: /usr/bin/google-chrome-stable
  chromium: /usr/bin/chromium
  firefox: /usr/bin/firefox
  edge: /usr/bin/microsoft-edge

# Directory paths (user mode)
directories:
  desktop: ~/.local/share/applications
  icons: ~/.local/share/icons/pwa-forge
  wrappers: ~/.local/bin/pwa-forge-wrappers
  apps: ~/.local/share/pwa-forge/apps
  userscripts: ~/.local/share/pwa-forge/userscripts

# Default flags for Chrome/Chromium
chrome_flags:
  enable:
    - WebUIDarkMode
  disable:
    - IntentPickerPWALinks
    - DesktopPWAsStayInWindow

# Default out-of-scope behavior
out_of_scope: open-in-default

# URL scheme for external links
external_link_scheme: ff

# Logging
log_level: info
log_file: ~/.local/share/pwa-forge/pwa-forge.log
```

### Per-App Manifest (`manifest.yaml`)

```yaml
# Unique application identifier
id: chatgpt-dnai

# Display name
name: ChatGPT-DNAI

# Application URL
url: https://chat.openai.com

# Browser configuration
browser: chrome
profile: ~/.config/pwa-forge/apps/chatgpt-dnai

# Visual assets
icon: ~/.local/share/icons/pwa-forge/chatgpt-dnai.svg
comment: ChatGPT as standalone application

# Window manager integration
wm_class: ChatGPTDnai
categories:
  - Network
  - Utility

# Browser flags
flags:
  ozone_platform: x11
  enable_features:
    - WebUIDarkMode
  disable_features:
    - IntentPickerPWALinks
    - DesktopPWAsStayInWindow

# Link handling
out_of_scope: open-in-default
inject:
  userscript: userscripts/external-links.user.js
  userscript_scheme: ff

# Metadata
created: 2025-10-22T10:30:00Z
modified: 2025-10-22T10:30:00Z
version: 1
```

### Registry Index (`registry.json`)

```json
{
  "version": 1,
  "apps": [
    {
      "id": "chatgpt-dnai",
      "name": "ChatGPT-DNAI",
      "url": "https://chat.openai.com",
      "manifest_path": "~/.local/share/pwa-forge/apps/chatgpt-dnai/manifest.yaml",
      "desktop_file": "~/.local/share/applications/pwa-forge-chatgpt-dnai.desktop",
      "wrapper_script": "~/.local/bin/pwa-forge-wrappers/chatgpt-dnai",
      "status": "active"
    }
  ],
  "handlers": [
    {
      "scheme": "ff",
      "browser": "firefox",
      "desktop_file": "~/.local/share/applications/pwa-forge-handler-ff.desktop",
      "script": "~/.local/bin/pwa-forge-handler-ff"
    }
  ]
}
```

## File Templates

### Desktop File Template (`.desktop`)

```ini
[Desktop Entry]
Type=Application
Name={{ name }}
Comment={{ comment | default(name + " PWA") }}
Exec={{ wrapper_path }} %U
Icon={{ icon_path }}
Terminal=false
Categories={{ categories | join(';') }};
StartupWMClass={{ wm_class }}
X-DBUS-StartupNotify=false
```

### Wrapper Script Template

```bash
#!/bin/bash
# Generated by pwa-forge
# App: {{ name }}
# ID: {{ id }}

exec "{{ browser_exec }}" \
  --class="{{ wm_class }}" \
  --ozone-platform={{ ozone_platform }} \
  --app="{{ url }}" \
  --user-data-dir="{{ profile }}" \
  {% if enable_features %}--enable-features={{ enable_features | join(',') }} \{% endif %}
  {% if disable_features %}--disable-features={{ disable_features | join(',') }} \{% endif %}
  {% if additional_flags %}{{ additional_flags }} \{% endif %}
  "$@"
```

### URL Scheme Handler Script Template

```bash
#!/bin/bash
# Generated by pwa-forge
# Scheme: {{ scheme }}://
# Target browser: {{ browser }}

raw="$1"

if [ -z "$raw" ]; then
  echo "Error: No URL provided" >&2
  exit 1
fi

# Remove scheme prefix
payload="${raw#{{ scheme }}:}"
payload="${payload#//}"

# Decode URL
decoded=$(python3 -c "
import sys
import urllib.parse as up
try:
    print(up.unquote(sys.argv[1]))
except Exception as e:
    print('Error decoding URL:', e, file=sys.stderr)
    sys.exit(1)
" "$payload")

if [ $? -ne 0 ]; then
  exit 1
fi

# Validate URL scheme
case "$decoded" in
  http://*|https://*)
    # Log the action (optional)
    logger -t pwa-forge-handler "Opening: $decoded"

    # Launch browser
    exec "{{ browser_exec }}" --new-window "$decoded"
    ;;
  *)
    echo "Error: Invalid URL scheme: $decoded" >&2
    logger -t pwa-forge-handler "Rejected URL: $decoded"
    exit 1
    ;;
esac
```

### Userscript Template

```javascript
// ==UserScript==
// @name         PWA Forge External Link Handler
// @namespace    pwa-forge
// @version      1.0
// @description  Redirects external links to custom URL scheme
// @match        {{ url_pattern }}
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function() {
  'use strict';

  const IN_SCOPE_HOSTS = {{ in_scope_hosts | tojson }};
  const SCHEME = '{{ scheme }}';

  function isExternal(url) {
    try {
      const u = new URL(url, location.href);
      return !IN_SCOPE_HOSTS.includes(u.host);
    } catch (e) {
      return false;
    }
  }

  function rewriteClicks(e) {
    if (e.defaultPrevented) return;
    if (e.button !== 0) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

    let a = e.target.closest('a[href]');
    if (!a) return;

    const href = a.getAttribute('href');
    if (!href) return;
    if (href.startsWith('mailto:') || href.startsWith('tel:')) return;

    if (isExternal(href)) {
      const targetUrl = new URL(href, location.href).toString();
      const encoded = encodeURIComponent(targetUrl);
      const newHref = SCHEME + ':' + encoded;

      e.preventDefault();
      setTimeout(() => { location.href = newHref; }, 0);
    }
  }

  function rewriteAnchors(root = document) {
    root.querySelectorAll('a[href]').forEach(a => {
      try {
        const href = a.getAttribute('href');
        if (!href) return;
        if (href.startsWith('mailto:') || href.startsWith('tel:')) return;

        if (isExternal(href)) {
          const targetUrl = new URL(href, location.href).toString();
          a.setAttribute('href', SCHEME + ':' + encodeURIComponent(targetUrl));
          a.setAttribute('target', '_blank');
          a.setAttribute('rel', 'noopener noreferrer');
        }
      } catch (e) {}
    });
  }

  const originalOpen = window.open;
  function patchedOpen(url, name, specs) {
    try {
      if (typeof url === 'string' && isExternal(url)) {
        const encoded = encodeURIComponent(new URL(url, location.href).toString());
        return originalOpen.call(window, SCHEME + ':' + encoded, name, specs);
      }
    } catch (e) {}
    return originalOpen.apply(window, arguments);
  }

  Object.defineProperty(window, 'open', {
    configurable: true,
    writable: true,
    value: patchedOpen
  });

  document.addEventListener('click', rewriteClicks, {capture: true});

  const observer = new MutationObserver(mutations => {
    for (const m of mutations) {
      if (m.addedNodes) {
        m.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            rewriteAnchors(node);
          }
        });
      }
    }
  });

  observer.observe(document, {childList: true, subtree: true});

  window.addEventListener('load', () => rewriteAnchors());
})();
```

### Handler Desktop File Template

```ini
[Desktop Entry]
Type=Application
Name=Open in {{ browser | title }} ({{ scheme }} handler)
Comment=Handle {{ scheme }}:// URLs
Exec={{ handler_script }} %u
Terminal=false
MimeType=x-scheme-handler/{{ scheme }};
Icon={{ icon | default('web-browser') }}
Categories=Network;
NoDisplay=true
```

## Non-Functional Requirements

### Performance
- Command execution should complete in < 2 seconds for typical operations
- Registry lookups should be cached in memory
- Dry-run mode should have minimal overhead

### Security
- URL scheme handlers must whitelist only http/https protocols
- All file operations must validate paths to prevent directory traversal
- Profile directories should have restricted permissions (0700)
- Handler scripts must sanitize and validate input URLs
- Userscripts should not be auto-enabled without user consent

### Compatibility
- Support Python 3.8+
- Work on X11 and Wayland (with X11 XWayland fallback)
- Support KDE Plasma 5.x, 6.x, GNOME 40+, and other XDG-compliant environments
- Chrome/Chromium 90+, Firefox 88+

### Maintainability
- Modular architecture with clear separation of concerns
- Comprehensive logging with configurable verbosity
- All templates should be externalized and easily customizable
- Full test coverage (unit + integration)

### Usability
- Clear error messages with actionable suggestions
- Progress indicators for long operations
- Colorized output for terminal (with --no-color flag)
- Shell completion for bash and zsh
- Comprehensive help text and examples

## Architecture

### Module Structure

```
pwa-forge/
├── pwa_forge/
│   ├── __init__.py
│   ├── __main__.py              # Entry point
│   ├── cli.py                   # Click CLI definitions
│   ├── config.py                # Configuration management
│   ├── registry.py              # App registry operations
│   ├── templates.py             # Template rendering (Jinja2)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── add.py               # add command implementation
│   │   ├── list.py              # list command implementation
│   │   ├── remove.py            # remove command implementation
│   │   ├── audit.py             # audit command implementation
│   │   ├── sync.py              # sync command implementation
│   │   ├── edit.py              # edit command implementation
│   │   ├── handler.py           # handler management commands
│   │   ├── userscript.py        # userscript generation
│   │   └── config_cmd.py        # config command implementation
│   ├── system/
│   │   ├── __init__.py
│   │   ├── desktop.py           # Desktop file operations
│   │   ├── xdg.py               # XDG utilities (mime, desktop-database)
│   │   ├── browser.py           # Browser detection and execution
│   │   └── permissions.py       # File permissions and sudo handling
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── url.py               # URL validation
│   │   ├── manifest.py          # Manifest schema validation
│   │   └── system.py            # System requirements validation
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # Logging configuration
│       ├── paths.py             # Path utilities
│       └── subprocess.py        # Subprocess wrappers
├── templates/                   # Jinja2 templates
│   ├── desktop.j2
│   ├── wrapper.j2
│   ├── userscript.j2
│   ├── handler-script.j2
│   └── handler-desktop.j2
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── README.md
│   ├── USAGE.md
│   ├── TROUBLESHOOTING.md
│   └── examples/
├── setup.py
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

### Key Components

#### CLI Layer (`cli.py`)
- Uses Click framework for command parsing
- Defines all commands and options
- Handles verbosity levels and dry-run mode
- Provides rich help text and examples

#### Configuration Manager (`config.py`)
- Loads and validates global configuration
- Provides defaults for missing values
- Handles both user and system mode paths
- Supports environment variable overrides

#### Registry Manager (`registry.py`)
- Maintains index of managed PWAs
- CRUD operations for app entries
- Validates registry consistency
- Thread-safe file operations

#### Template Engine (`templates.py`)
- Jinja2-based template rendering
- Custom filters for path expansion and escaping
- Validates rendered output
- Caches compiled templates

#### System Bridge (`system/`)
- **desktop.py**: Creates and validates .desktop files
- **xdg.py**: Wraps xdg-utils commands
- **browser.py**: Detects and launches browsers
- **permissions.py**: Handles file permissions and sudo escalation

#### Validators (`validation/`)
- URL accessibility and format validation
- YAML schema validation for manifests
- System requirements checking (browsers, XDG tools)

### Data Flow

1. **Add Command Flow:**
   ```
   User input → Validation → Manifest creation → Template rendering →
   File writing → XDG registration → Registry update
   ```

2. **Audit Command Flow:**
   ```
   Registry lookup → File existence checks → Content validation →
   Runtime tests → Report generation
   ```

3. **Link Redirection Flow:**
   ```
   User clicks link in PWA → Userscript intercepts → Rewrites to ff:// →
   XDG launches handler → Handler decodes URL → Opens in system browser
   ```

## Testing Requirements

### Unit Tests
- Template rendering with various inputs
- Configuration loading and merging
- Path utilities and expansion
- URL validation logic
- Manifest YAML parsing
- Registry operations

### Integration Tests
- Full add/remove/list cycle
- Desktop file generation and registration
- Handler script generation and execution
- Audit command with mock PWAs
- Dry-run mode verification

### System Tests (Manual)
- End-to-end PWA creation and launch
- External link opening in correct browser
- Window manager integration (WMClass)
- Icon display in launchers
- Multiple PWAs with same base URL
- Profile isolation verification

### Test Fixtures
- Sample manifests for various configurations
- Mock browser executables
- Temporary test directories
- Mock XDG environment

## Error Handling

### Error Categories
1. **User Input Errors**: Invalid URLs, missing files, bad IDs
2. **System Errors**: Missing executables, permission denied, disk full
3. **Configuration Errors**: Invalid YAML, missing required fields
4. **Runtime Errors**: Browser crashes, handler failures

### Error Response Strategy
- All errors should have unique error codes
- Error messages must be actionable (suggest fix)
- Errors should be logged with full context
- Exit codes should follow standard conventions (0=success, 1-255=error types)

### Example Error Messages
```
Error: PWA 'chatgpt' not found in registry
  → Run 'pwa-forge list' to see available PWAs
  → Use 'pwa-forge add' to create a new PWA

Error: Browser executable not found: /usr/bin/google-chrome-stable
  → Install Chrome: sudo apt install google-chrome-stable
  → Or use a different browser: pwa-forge add --browser firefox <url>

Error: Permission denied: /usr/local/bin/pwa-forge-handler-ff
  → System-wide installation requires sudo
  → Run: sudo pwa-forge install-handler --scheme ff --system
  → Or use user mode (default): pwa-forge install-handler --scheme ff
```

## Logging

### Log Levels
- **DEBUG**: Template rendering, subprocess calls, file operations
- **INFO**: Command execution, PWA creation/removal, handler registration
- **WARNING**: Deprecated flags, missing optional dependencies
- **ERROR**: Operation failures, validation errors

### Log Format
```
[2025-10-22 10:30:45] [INFO] pwa_forge.commands.add: Creating PWA 'ChatGPT' (chatgpt-dnai)
[2025-10-22 10:30:45] [DEBUG] pwa_forge.templates: Rendering template: wrapper.j2
[2025-10-22 10:30:45] [DEBUG] pwa_forge.system.desktop: Writing desktop file: /home/user/.local/share/applications/pwa-forge-chatgpt-dnai.desktop
[2025-10-22 10:30:46] [INFO] pwa_forge.commands.add: PWA created successfully
```

### Log Output
- Console: INFO and above (configurable via --quiet/--verbose/--debug)
- File: DEBUG and above (rotated daily, keep 7 days)
- Location: `~/.local/share/pwa-forge/pwa-forge.log`

## Dependencies

### Python Requirements
```
Python >= 3.8

Required:
- click >= 8.0.0
- jinja2 >= 3.0.0
- pyyaml >= 6.0
- requests >= 2.28.0

Development:
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- black >= 22.0.0
- ruff >= 0.1.0
- mypy >= 1.0.0
```

### System Requirements
- One of: google-chrome-stable, chromium, firefox, microsoft-edge
- xdg-utils (xdg-mime, update-desktop-database)
- Python 3.8+ with pip

### Optional Dependencies
- ViolentMonkey/Tampermonkey browser extension (for userscript injection)
- ImageMagick (for icon conversion)

## Deployment

### Installation Methods

**Note:** PWA Forge is not yet published to PyPI. Install from source:

#### From Source (Recommended)
```bash
git clone https://github.com/bigr/pwa_forge.git
cd pwa_forge
pip install -e .
```

#### Via pip with git
```bash
pip install git+https://github.com/bigr/pwa_forge.git
```

#### From PyPI (Future)
```bash
pip install pwa-forge  # Not yet available
```

#### System Package (Future)
```bash
# Debian/Ubuntu
sudo apt install pwa-forge

# Fedora
sudo dnf install pwa-forge
```

### Post-Installation Setup
```bash
# Install shell completion
pwa-forge --install-completion zsh
pwa-forge --install-completion bash

# Verify installation
pwa-forge doctor

# Initialize configuration
pwa-forge config set default_browser chrome
```

---

## System Packaging Options

**pwa-forge** is currently distributed via PyPI (`pip install pwa-forge`). For broader distribution and easier system integration, consider packaging for native package managers.

### Recommended Packaging Formats

#### 1. **Debian/Ubuntu (.deb) Package** ⭐ **RECOMMENDED**

**Pros:**
- Native integration with apt/dpkg
- Proper dependency management (python3, xdg-utils, browsers)
- Easy installation for Debian/Ubuntu/Mint users
- Can be hosted in PPA (Personal Package Archive)

**Implementation Steps:**
1. Create `debian/` directory with packaging metadata
2. Use `stdeb` or `dh-virtualenv` to build .deb from Python package
3. Define dependencies: `python3 (>= 3.10), xdg-utils, python3-click, python3-jinja2, python3-yaml, python3-requests`
4. Add post-install script to suggest browser installation
5. Host in Launchpad PPA or GitHub releases

**Files needed:**
```
debian/
├── control         # Package metadata and dependencies
├── rules           # Build instructions
├── changelog       # Version history
├── copyright       # License information
├── compat          # Debhelper compatibility level
└── postinst        # Post-installation script (optional)
```

**Example `debian/control`:**
```
Source: pwa-forge
Section: utils
Priority: optional
Maintainer: Pavel Klinger <ja@bigr.cz>
Build-Depends: debhelper (>= 10), python3-all, dh-python, python3-setuptools
Standards-Version: 4.5.0

Package: pwa-forge
Architecture: all
Depends: ${python3:Depends}, ${misc:Depends},
         python3 (>= 3.10),
         python3-click (>= 8.1),
         python3-jinja2 (>= 3.1),
         python3-yaml (>= 6.0),
         python3-requests (>= 2.28),
         xdg-utils
Recommends: google-chrome-stable | chromium-browser | firefox
Description: Manage Progressive Web Apps as native-feeling Linux launchers
 pwa-forge automates the creation of isolated browser instances with custom
 launchers, handles external link redirection to system browsers, and provides
 comprehensive PWA lifecycle management.
```

**Build command:**
```bash
# Using stdeb
python3 setup.py --command-packages=stdeb.command bdist_deb

# Or using debuild
debuild -us -uc
```

**Installation:**
```bash
sudo apt install ./pwa-forge_0.1.0-1_all.deb
```

---

#### 2. **Flatpak** ⭐ **RECOMMENDED FOR SANDBOXING**

**Pros:**
- Works across all Linux distributions (Debian, Fedora, Arch, etc.)
- Available via Flathub (central app store)
- Sandboxed execution with defined permissions
- Bundles all dependencies (no system conflicts)

**Cons:**
- More complex setup (needs runtime, SDK)
- Larger package size (includes Python runtime)
- Flatpak applications run in sandbox (may need filesystem permissions for ~/.local/share)

**Implementation Steps:**
1. Create `com.bigr.pwa-forge.yaml` manifest
2. Define Python runtime (org.freedesktop.Sdk.Extension.python3)
3. Build with `flatpak-builder`
4. Submit to Flathub for distribution

**Example manifest (`com.bigr.pwaforge.flatpak.yaml`):**
```yaml
app-id: com.bigr.pwaforge
runtime: org.freedesktop.Platform
runtime-version: '23.08'
sdk: org.freedesktop.Sdk
command: pwa-forge

finish-args:
  # Access to home directory for .local/share and .config
  - --filesystem=home
  # Access to XDG directories
  - --filesystem=xdg-config/pwa-forge:create
  - --filesystem=xdg-data/pwa-forge:create
  - --filesystem=xdg-data/applications:create
  - --filesystem=xdg-data/icons:create
  # Talk to session bus for desktop integration
  - --socket=session-bus
  # Allow running xdg-utils commands
  - --share=network

modules:
  - name: pwa-forge
    buildsystem: simple
    build-commands:
      - pip3 install --prefix=/app --no-deps .
    sources:
      - type: archive
        url: https://github.com/bigr/pwa_forge/archive/refs/tags/v0.1.0.tar.gz
        sha256: <checksum>
```

**Build and install:**
```bash
flatpak-builder --force-clean build-dir com.bigr.pwaforge.flatpak.yaml
flatpak-builder --user --install --force-clean build-dir com.bigr.pwaforge.flatpak.yaml
```

**Run:**
```bash
flatpak run com.bigr.pwaforge add https://example.com
```

---

#### 3. **Snap Package**

**Pros:**
- Works on Ubuntu and other distros with snapd
- Automatic updates via Snap Store
- Sandboxed with defined interfaces

**Cons:**
- Requires snapd (not installed by default on non-Ubuntu)
- Larger package size
- Slower startup due to squashfs mounting

**Implementation Steps:**
1. Create `snapcraft.yaml`
2. Define Python base and dependencies
3. Build with `snapcraft`
4. Publish to Snap Store

**Example `snapcraft.yaml`:**
```yaml
name: pwa-forge
version: '0.1.0'
summary: Manage Progressive Web Apps as native-feeling Linux launchers
description: |
  pwa-forge automates the creation of isolated browser instances with custom
  launchers, handles external link redirection to system browsers, and provides
  comprehensive PWA lifecycle management.

base: core22
confinement: classic  # Needs classic for filesystem access and browser launching
grade: stable

apps:
  pwa-forge:
    command: bin/pwa-forge
    plugs:
      - home
      - desktop
      - network

parts:
  pwa-forge:
    plugin: python
    source: .
    python-packages:
      - click>=8.1
      - jinja2>=3.1
      - pyyaml>=6.0
      - requests>=2.28
    stage-packages:
      - xdg-utils
```

**Build and install:**
```bash
snapcraft
sudo snap install pwa-forge_0.1.0_amd64.snap --classic
```

---

#### 4. **Arch User Repository (AUR)**

**Pros:**
- De facto standard for Arch/Manjaro users
- Community-maintained packages
- Easy installation via AUR helpers (yay, paru)

**Implementation Steps:**
1. Create `PKGBUILD` file
2. Submit to AUR
3. Users install with `yay -S pwa-forge`

**Example `PKGBUILD`:**
```bash
# Maintainer: Pavel Klinger <ja@bigr.cz>
pkgname=pwa-forge
pkgver=0.1.0
pkgrel=1
pkgdesc="Manage Progressive Web Apps as native-feeling Linux launchers"
arch=('any')
url="https://github.com/bigr/pwa_forge"
license=('MIT')
depends=(
    'python>=3.10'
    'python-click>=8.1'
    'python-jinja>=3.1'
    'python-yaml>=6.0'
    'python-requests>=2.28'
    'xdg-utils'
)
optdepends=(
    'google-chrome: Chromium-based PWA support'
    'chromium: Open-source Chromium-based PWA support'
    'firefox: Firefox-based PWA support'
)
makedepends=('python-build' 'python-installer' 'python-wheel')
source=("$pkgname-$pkgver.tar.gz::https://github.com/bigr/pwa_forge/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
}
```

**Installation by users:**
```bash
yay -S pwa-forge
```

---

#### 5. **Fedora/RHEL (.rpm) Package**

**Pros:**
- Native integration with dnf/yum
- Standard for Red Hat-based distributions

**Implementation Steps:**
1. Create `.spec` file
2. Build with `rpmbuild`
3. Submit to Fedora Copr or host in own repo

**Example `pwa-forge.spec`:**
```spec
Name:           pwa-forge
Version:        0.1.0
Release:        1%{?dist}
Summary:        Manage Progressive Web Apps as native-feeling Linux launchers
License:        MIT
URL:            https://github.com/bigr/pwa_forge
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
Requires:       python3 >= 3.10
Requires:       python3-click >= 8.1
Requires:       python3-jinja2 >= 3.1
Requires:       python3-pyyaml >= 6.0
Requires:       python3-requests >= 2.28
Requires:       xdg-utils
Recommends:     chromium-browser
Recommends:     firefox

%description
pwa-forge automates the creation of isolated browser instances with custom
launchers, handles external link redirection to system browsers, and provides
comprehensive PWA lifecycle management.

%prep
%autosetup

%build
%py3_build

%install
%py3_install

%files
%license LICENSE
%doc README.md
%{_bindir}/pwa-forge
%{python3_sitelib}/pwa_forge/
%{python3_sitelib}/pwa_forge-*.egg-info/

%changelog
* Thu Oct 23 2025 Pavel Klinger <ja@bigr.cz> - 0.1.0-1
- Initial package
```

**Build:**
```bash
rpmbuild -ba pwa-forge.spec
```

---

### Packaging Priority Recommendations

**For maximum reach and ease of use:**

1. **Start with:** Debian/Ubuntu .deb package + PPA
   - Largest user base (Ubuntu, Debian, Mint, Pop!_OS, etc.)
   - Simple to create with `stdeb`
   - Can be hosted on GitHub releases or Launchpad PPA

2. **Then add:** AUR for Arch users
   - Very simple to create (just PKGBUILD)
   - Community will maintain it if popular
   - Standard practice for Arch ecosystem

3. **Consider:** Flatpak for universal distribution
   - Works everywhere, but more complex setup
   - Good for users who want sandboxing
   - Flathub provides central discovery

4. **Optional:** RPM for Fedora/RHEL and Snap for Ubuntu

### Quick Start: Creating .deb Package

**Easiest approach using `stdeb`:**

```bash
# Install build dependencies
sudo apt install python3-stdeb dh-python

# Generate debian/ directory
python3 setup.py --command-packages=stdeb.command debianize

# Customize debian/control if needed
# Then build package
dpkg-buildpackage -us -uc

# Result: ../pwa-forge_0.1.0-1_all.deb
```

**Advantages of native packages over pip:**
- System-wide installation (no virtualenv needed)
- Dependency tracking (apt/dnf knows what's installed)
- Easy upgrades (`apt upgrade pwa-forge`)
- Uninstall cleans up everything (`apt remove pwa-forge`)
- Pre/post install scripts for system integration
- Distribution repositories provide trust/verification

---

## Development Workflow

### Setup Development Environment
```bash
git clone <repo-url>
cd pwa-forge
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements-dev.txt
pip install -e .
```

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=pwa_forge --cov-report=html

# Specific test file
pytest tests/unit/test_templates.py

# Integration tests only
pytest tests/integration/
```

### Code Quality
```bash
# Format code
black pwa_forge tests

# Lint
ruff check pwa_forge tests

# Type check
mypy pwa_forge
```

### Running Locally
```bash
# Run without installation
python -m pwa_forge add https://example.com --dry-run

# Or use installed editable package
pwa-forge --help
```

### Debugging
- Set breakpoints in code
- Use `--debug` flag for verbose logging
- Check log file at `~/.local/share/pwa-forge/pwa-forge.log`
- Use `--dry-run` to see operations without execution

## Future Enhancements (Out of Scope for MVP)

1. **GUI Management Interface**: Qt/GTK application for non-CLI users
2. **PWA Auto-Discovery**: Detect installed PWAs from Chrome/Firefox
3. **Icon Fetching**: Automatic download of app icons from manifests
4. **Wayland Native Support**: Better integration without X11 fallback
5. **Multi-Browser Profiles**: Support multiple browser engines per app
6. **Backup/Restore**: Export and import PWA configurations
7. **Update Notifications**: Notify when web apps have updates
8. **Sandboxing**: Additional security via firejail/bubblewrap
9. **Analytics**: Optional telemetry for usage patterns
10. **Plugin System**: Allow community extensions

## Security Considerations

### Threat Model
1. **Malicious URLs**: Handler scripts could be tricked into opening harmful URLs
2. **Path Traversal**: File operations could write outside intended directories
3. **Code Injection**: Template rendering could execute arbitrary code
4. **Privilege Escalation**: Improper sudo handling could allow privilege escalation

### Mitigations
1. **URL Whitelisting**: Only allow http/https in handler scripts
2. **Path Validation**: All file operations validate and normalize paths
3. **Template Sandboxing**: Jinja2 autoescape enabled, no eval()
4. **Explicit Sudo**: Never auto-elevate; always prompt user to run sudo commands
5. **Input Sanitization**: All user input is validated and sanitized
6. **File Permissions**: Generated scripts are not world-writable

## Documentation Requirements

### README.md
- Quick start guide
- Installation instructions
- Basic usage examples
- Link to full documentation

### USAGE.md
- Detailed command reference
- Advanced configuration examples
- Troubleshooting common issues
- FAQ

### CONTRIBUTING.md
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

### API Documentation
- Inline docstrings for all public functions
- Sphinx-generated HTML docs (optional for MVP)

## Acceptance Criteria

### Minimum Viable Product (MVP)
The following must work reliably:

1. ✅ `pwa-forge add` creates a functional PWA that launches correctly
2. ✅ Generated `.desktop` file appears in system launcher
3. ✅ PWA uses isolated profile (no data mixing with regular browser)
4. ✅ `pwa-forge list` shows all managed PWAs
5. ✅ `pwa-forge remove` cleanly removes PWA
6. ✅ `pwa-forge generate-handler` creates functional handler script
7. ✅ `pwa-forge install-handler` registers handler with XDG
8. ✅ External links from PWA open in system browser (when userscript enabled)
9. ✅ `pwa-forge audit` detects broken configurations
10. ✅ All core operations work without sudo (user mode)
11. ✅ Help text is comprehensive and includes examples
12. ✅ Unit test coverage > 70%
13. ✅ Integration tests cover add/remove/list/audit flows
14. ✅ Tool gracefully handles missing dependencies
15. ✅ Error messages are actionable

### Success Metrics
- User can create a PWA in < 30 seconds with single command
- External links open in correct browser 100% of time (when userscript works)
- Zero data corruption or file permission issues
- Clear error messages for all failure modes

## Implementation Phases

### Phase 1: Core Infrastructure ✅ COMPLETED
- [X] Project scaffolding and package structure
- [X] CLI framework (Click) with basic commands
- [X] Configuration system (YAML loading)
- [X] Template engine (Jinja2) with basic templates
- [X] Logging setup
- [X] Path utilities

### Phase 2: Basic PWA Management ✅ COMPLETED
- [X] `add` command implementation
  - [X] URL validation
  - [X] Profile directory creation
  - [X] Wrapper script generation
  - [X] Desktop file generation
  - [X] Icon handling (copy from path)
  - [X] Registry entry creation
- [X] `list` command implementation
  - [X] Table format output
  - [X] JSON/YAML format support
  - [X] Verbose mode
- [X] `remove` command implementation
  - [X] Safe file deletion
  - [X] Profile cleanup option
  - [X] Registry update
- [X] Registry management
  - [X] JSON-based index
  - [X] CRUD operations
  - [X] Locking for concurrent access

### Phase 3: Browser Integration Test Framework
- [X] Tooling setup
  - [X] Add Playwright to project dependencies (`optional-dev` extra)
  - [X] Provide `tox` environment for Playwright tests (headless only)
  - [X] Document local browser driver requirements and installation steps
  - [ ] Optional: scaffold `npm` workspace with Jest + jsdom for fast JS unit tests (userscript helpers)
- [X] Test harness
  - [X] Create fixtures to spin up temporary test PWAs (wrapper, desktop file, userscript)
  - [X] Implement utilities for launching Playwright in headless mode with injected userscript
  - [X] Capture logs and screenshots on failure for CI artifacts
- [X] Core scenarios
  - [X] External link rewrite: confirm `userscript.j2` rewrites links to custom scheme
  - [X] Window opening: ensure `window.open` calls use custom scheme
  - [X] Handler integration: verify handler script receives decoded URL and launches browser stub
- [X] CI integration
  - [X] Run Playwright smoke suite in GitHub Actions (Linux, Chromium)
  - [X] Allow opt-out via env flag for contributors without browsers installed
  - [X] Publish HTML reports as build artifacts
  - [ ] Optional: run Jest unit suite in Node.js workflow for rapid feedback

### Phase 4: URL Handler System ✅ COMPLETED
- [X] `generate-handler` command
  - [X] Template rendering
  - [X] URL decoding logic
  - [X] Security validation
  - [X] Multiple browser support
- [X] `install-handler` command
  - [X] Desktop file creation for handler
  - [X] XDG mime registration
  - [X] Verification of registration
- [X] `generate-userscript` command
  - [X] Template with configurable scheme
  - [X] In-scope host configuration
  - [X] Instructions for manual installation

### Phase 5: Validation & Audit ✅ COMPLETED
- [X] `audit` command implementation
  - [X] File existence checks (desktop, wrapper, manifest, profile, icon)
  - [X] Desktop file validation (parse INI, check required keys)
  - [X] Wrapper script validation (executable bit, valid bash syntax)
  - [X] Profile directory validation (exists, is directory, has permissions)
  - [X] Handler registration check (query xdg-mime for scheme handlers)
  - [X] Browser executable check (exists and is executable)
  - [X] Fix mode (--fix flag): regenerate missing/broken files using sync logic
  - [X] Report format: table with PASS/FAIL, error messages, and suggestions
  - [X] Exit code: 0 if all pass, 1 if any fail
- [X] `sync` command
  - [X] Load manifest YAML file
  - [X] Validate manifest schema (using validation.py)
  - [X] Regenerate wrapper script from template
  - [X] Regenerate desktop file from template
  - [X] Update file permissions (wrapper: 0755)
  - [X] Detect and warn about manual changes (compare timestamps)
  - [X] Update modified timestamp in manifest
- [X] `edit` command
  - [X] Resolve app ID to manifest path using registry
  - [X] Validate $EDITOR environment variable is set
  - [X] Open manifest in $EDITOR (subprocess.run with wait)
  - [X] Validate YAML after edit (syntax and schema)
  - [X] Offer to sync if validation passes
  - [X] Rollback to backup if validation fails

### Phase 6: Testing & Polish ✅ COMPLETED
- [X] Unit tests (DONE - comprehensive coverage)
  - [X] Template rendering tests
  - [X] Configuration loading tests
  - [X] Path utilities tests
  - [X] Validation logic tests
  - [X] Registry operations tests
  - [X] Handler and userscript generation tests
- [X] Integration tests (DONE - lifecycle covered)
  - [X] Add/list/remove cycle
  - [X] Handler generation and registration workflow
  - [X] Dry-run mode
- [X] Playwright browser tests (DONE - userscript and handler verified)
  - [X] External link rewriting
  - [X] window.open() patching
  - [X] Handler script URL decoding
- [X] E2E System Tests (DONE - comprehensive automation)
  - [X] Test add command with actual browser detection
  - [X] Test XDG desktop database update (mock xdg-utils)
  - [X] Test handler registration with xdg-mime (mock)
  - [X] Test audit command detects real file issues
  - [X] Test sync regenerates valid artifacts
  - [X] Test edit command with temporary EDITOR
  - [X] Test complete PWA workflow (add -> list -> audit -> sync -> remove)
- [X] Documentation (DONE)
  - [X] README with quick start
  - [X] TESTING.md with comprehensive guide
  - [X] USAGE.md with detailed examples
  - [X] TROUBLESHOOTING.md with common issues
  - [X] Inline help text refinement
- [X] Code quality (DONE)
  - [X] Linting with ruff
  - [X] Type hints with mypy
  - [X] Code formatting with ruff format
  - [X] Pre-commit hooks
  - [X] Verify 70%+ test coverage (74% achieved)

### Phase 7: Release Preparation & Polish ✅ COMPLETED (Core Features)
- [X] Package for PyPI (DONE)
  - [X] pyproject.toml configuration
  - [X] version management (__version__ in __init__.py)
  - [X] dependencies declaration
  - [X] Entry point script (pwa-forge command)
- [X] Shell completion scripts ✅ COMPLETED
  - [X] Bash completion (use click.shell_completion)
  - [X] Zsh completion (use click.shell_completion)
  - [X] Fish completion (use click.shell_completion)
  - [X] Add completion command to display instructions
- [X] `doctor` command ✅ COMPLETED
  - [X] Check Python version (>= 3.10)
  - [X] Detect available browsers (chrome, chromium, firefox, edge)
  - [X] Check xdg-utils presence (xdg-mime, update-desktop-database)
  - [X] Verify directory permissions (can write to ~/.local/share, ~/.local/bin)
  - [X] Check desktop environment (detect KDE/GNOME/other)
  - [X] Validate config file if exists
  - [X] Validate registry file if exists
  - [X] Check optional dependencies (Playwright)
  - [X] Display summary table with PASS/FAIL/WARNING/INFO
- [X] Config commands implementation ✅ COMPLETED
  - [X] config get: read key from config YAML (supports dot notation)
  - [X] config set: update key in config YAML, validate value
  - [X] config list: display all config values formatted
  - [X] config reset: restore default config.yaml (delete user file)
  - [X] config edit: open in $EDITOR with validation (reuse edit command logic)
- [ ] Error handling polish (OPTIONAL - Future Enhancement)
  - [ ] Define error code enum (1-10 for different error types)
  - [X] Ensure all commands return appropriate exit codes
  - [X] Review all error messages for actionability
  - [X] Add suggestions to error messages (e.g., "Run: pwa-forge doctor")
- [X] Documentation (DONE)
  - [X] Write USAGE.md with all commands documented
  - [X] Write TROUBLESHOOTING.md with FAQ
  - [X] Add CONTRIBUTING.md with development guide
  - [X] Update README badges (CI status, coverage)
- [ ] Release process (DEFERRED - Manual process)
  - [ ] Create CHANGELOG.md
  - [ ] Tag version 0.1.0
  - [ ] Build and test wheel
  - [ ] Publish to PyPI

---

## LLM Implementation Guide

This section provides detailed, actionable instructions for implementing remaining features using LLM-assisted coding.

### Implementation Order (Priority)

1. **Phase 5.1: Audit Command** (High Priority - enables validation)
2. **Phase 5.2: Sync Command** (High Priority - required by audit --fix)
3. **Phase 5.3: Edit Command** (Medium Priority - UX improvement)
4. **Phase 7.1: Config Commands** (Medium Priority - configuration management)
5. **Phase 7.2: Doctor Command** (High Priority - system diagnostics)
6. **Phase 7.3: Shell Completion** (Low Priority - convenience)
7. **Phase 6: E2E Test Suite** (High Priority - automated validation)
8. **Phase 7.4: Documentation** (Medium Priority - user-facing)

### Phase 5.1: Audit Command Implementation

**File to create:** `src/pwa_forge/commands/audit.py`

**Function signature:**
```python
def audit_app(
    app_id: str | None,
    config: Config,
    fix: bool = False,
    open_test_page: bool = False,
) -> dict[str, Any]:
    """
    Audit PWA configuration and optionally fix issues.

    Args:
        app_id: Application ID (None = audit all apps)
        config: Config instance
        fix: Attempt to repair broken configurations
        open_test_page: Launch PWA with test page

    Returns:
        Dict with audit results: {
            "audited_apps": int,
            "passed": int,
            "failed": int,
            "fixed": int,
            "results": [{"id": str, "checks": [{"name": str, "status": str, "message": str}]}]
        }
    """
```

**Checks to implement:**
1. **Manifest exists**: `manifest_path.exists()`
2. **Manifest valid YAML**: `yaml.safe_load()` doesn't raise
3. **Desktop file exists**: Check path from registry
4. **Desktop file valid**: Parse with configparser, check [Desktop Entry] section
5. **Wrapper script exists**: Check path from registry
6. **Wrapper script executable**: `path.stat().st_mode & 0o111 != 0`
7. **Profile directory exists**: Check from manifest
8. **Browser executable exists**: Use existing browser detection logic
9. **Icon exists** (if specified): Check icon path from manifest
10. **Handler registered** (if userscript configured): Query xdg-mime

**Fix mode logic:**
- Use sync command logic to regenerate wrapper and desktop files
- Update file permissions if incorrect
- Do NOT fix missing manifest (fatal error)
- Do NOT create missing profile directory (user data)

**Output format:**
- Table with columns: Check | Status | Message
- Color-coded: green ✓ for PASS, red ✗ for FAIL, yellow ⚠ for WARNING
- Summary: "X/Y checks passed"
- Exit code: 0 if all pass, 1 if any fail

**Integration with CLI:**
- Update `cli.py` audit command to call `audit_app()`
- Add error handling with AuditCommandError exception

**Tests to write:** `tests/unit/test_audit.py`
- Test all individual checks with mocked file system
- Test fix mode regenerates files
- Test audit all apps
- Test exit codes

### Phase 5.2: Sync Command Implementation

**File to create:** `src/pwa_forge/commands/sync.py`

**Function signature:**
```python
def sync_app(
    app_id: str,
    config: Config,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Regenerate all artifacts from manifest file.

    Args:
        app_id: Application ID
        config: Config instance
        dry_run: Show what would be regenerated

    Returns:
        Dict with sync results: {
            "id": str,
            "regenerated": ["wrapper", "desktop"],
            "warnings": [str],
        }
    """
```

**Implementation steps:**
1. Load manifest from `config.apps_dir / app_id / "manifest.yaml"`
2. Validate manifest schema (reuse `validation.validate_manifest_dict()`)
3. Check if wrapper/desktop files have been manually edited (compare mtime with manifest modified time)
4. Warn about manual changes
5. Regenerate wrapper script using template engine
6. Regenerate desktop file using template engine
7. Set file permissions (wrapper: 0755)
8. Update manifest modified timestamp
9. Update registry if paths changed

**Integration with CLI:**
- Update `cli.py` sync command to call `sync_app()`
- Add error handling with SyncCommandError exception

**Tests to write:** `tests/unit/test_sync.py`
- Test regenerates wrapper correctly
- Test regenerates desktop file correctly
- Test dry-run mode
- Test warning on manual changes
- Test updates manifest timestamp

### Phase 5.3: Edit Command Implementation

**File to create:** `src/pwa_forge/commands/edit.py`

**Function signature:**
```python
def edit_app(
    app_id: str,
    config: Config,
    auto_sync: bool = True,
) -> dict[str, Any]:
    """
    Open manifest in $EDITOR and optionally sync after edit.

    Args:
        app_id: Application ID
        config: Config instance
        auto_sync: Automatically sync after successful edit

    Returns:
        Dict with edit results: {
            "id": str,
            "edited": bool,
            "synced": bool,
            "validation_errors": [str] | None,
        }
    """
```

**Implementation steps:**
1. Resolve app ID to manifest path using registry
2. Check $EDITOR environment variable (fallback: vi, nano, then error)
3. Create backup: `manifest.yaml.bak`
4. Open manifest in editor: `subprocess.run([editor, manifest_path])`
5. Validate YAML syntax after edit
6. Validate manifest schema
7. If validation fails: restore backup, show errors, exit
8. If validation passes and auto_sync: call sync_app()
9. Remove backup on success

**Integration with CLI:**
- Update `cli.py` edit command to call `edit_app()`
- Add --no-sync flag to skip auto-sync
- Add error handling with EditCommandError exception

**Tests to write:** `tests/unit/test_edit.py`
- Mock $EDITOR and subprocess.run
- Test successful edit and sync
- Test validation failure restores backup
- Test missing $EDITOR error
- Test auto-sync flag

### Phase 7.1: Config Commands Implementation

**File to create:** `src/pwa_forge/commands/config_cmd.py`

**Functions to implement:**

```python
def config_get(key: str, config: Config) -> str:
    """Get config value by key (supports dot notation: browsers.chrome)."""

def config_set(key: str, value: str, config: Config) -> None:
    """Set config value by key, validate, and save."""

def config_list(config: Config) -> dict[str, Any]:
    """Return all config values as dict."""

def config_reset(config: Config) -> None:
    """Reset config to defaults."""

def config_edit(config: Config) -> None:
    """Open config file in $EDITOR."""
```

**Implementation details:**
- Dot notation parsing: `key.split('.')` to navigate nested dicts
- Validation: check value types match schema
- Save: write YAML to config file path
- Reset: delete user config file (falls back to defaults)

**Integration with CLI:**
- Update `cli.py` config subcommands to call these functions
- Format output nicely (YAML or key=value pairs)

**Tests to write:** `tests/unit/test_config_cmd.py`
- Test get with nested keys
- Test set updates and saves
- Test list returns all values
- Test reset deletes file
- Test edit opens $EDITOR

### Phase 7.2: Doctor Command Implementation

**File to create:** `src/pwa_forge/commands/doctor.py`

**Function signature:**
```python
def run_doctor(config: Config) -> dict[str, Any]:
    """
    Check system requirements and configuration.

    Returns:
        Dict with check results: {
            "checks": [{"name": str, "status": str, "message": str}],
            "passed": int,
            "failed": int,
            "warnings": int,
        }
    """
```

**Checks to implement:**
1. Python version >= 3.10
2. Browsers available (chrome, chromium, firefox, edge)
3. xdg-utils commands (xdg-mime, update-desktop-database)
4. Directory write permissions (~/.local/share, ~/.local/bin)
5. Desktop environment detection ($XDG_CURRENT_DESKTOP)
6. Config file valid (if exists)
7. Registry file valid (if exists)
8. Playwright installed (optional dependency)

**Output format:**
- Table: Check | Status | Message
- Status: PASS (green ✓), FAIL (red ✗), WARNING (yellow ⚠), INFO (blue ℹ)
- Summary line: "X checks passed, Y failed, Z warnings"

**Integration with CLI:**
- Add doctor command to cli.py
- Exit code: 0 if no failures, 1 if any fail

**Tests to write:** `tests/unit/test_doctor.py`
- Mock all system checks
- Test each check passes/fails appropriately
- Test output format

### E2E Testing Strategy

**Goal:** Automated tests that verify the full system without manual intervention.

**Approach:** Mock external system calls (xdg-utils, subprocess) but test real file operations.

**File to create:** `tests/e2e/test_full_workflow.py`

**Test scenarios:**

1. **Full PWA lifecycle with real files:**
   - Create temp directories for all paths
   - Run add command (real file creation)
   - Verify all files exist with correct content
   - Run list command, verify output
   - Run audit command, verify PASS
   - Manually corrupt a file
   - Run audit, verify FAIL
   - Run audit --fix, verify files repaired
   - Run sync command
   - Run edit command (mock $EDITOR to modify manifest)
   - Run remove command
   - Verify all files deleted

2. **Handler workflow with mocked XDG:**
   - Mock xdg-mime and update-desktop-database commands
   - Generate handler script
   - Install handler (verify desktop file created)
   - Verify xdg-mime was called with correct args
   - Test handler script execution with sample URL
   - Uninstall handler
   - Verify cleanup

3. **Config management:**
   - Test config get/set/list/reset
   - Verify file persistence
   - Test invalid value rejection

4. **Doctor command:**
   - Mock system state (browsers present/absent)
   - Run doctor
   - Verify accurate detection

**Mock strategy:**
- Use `unittest.mock.patch` for subprocess calls
- Use `pytest.MonkeyPatch` for environment variables
- Use real filesystem operations in temp directories
- Capture and verify mock call arguments

**CI integration:**
- Run E2E tests in GitHub Actions
- Use isolated temp directories
- Mock xdg-utils (not available in containers)
- Fast execution (no actual browser launches)

---

## Additional Technical Specifications

### ID Generation Rules

**Valid ID Format:**
- Lowercase only
- Alphanumeric plus `-` and `_`
- No spaces or special characters
- Maximum 64 characters
- Must start with letter or digit

**Auto-generation from Name:**
```python
def generate_id(name: str) -> str:
    """
    Generate a valid ID from a display name.

    Examples:
        "ChatGPT-DNAI" -> "chatgpt-dnai"
        "My App!" -> "my-app"
        "App   Name" -> "app-name"
    """
    import re
    # Convert to lowercase
    id_str = name.lower()
    # Replace spaces and special chars with hyphen
    id_str = re.sub(r'[^a-z0-9_-]+', '-', id_str)
    # Remove leading/trailing hyphens
    id_str = id_str.strip('-')
    # Collapse multiple hyphens
    id_str = re.sub(r'-+', '-', id_str)
    # Truncate if too long
    return id_str[:64]
```

### Desktop File Naming

**Convention:**
- Format: `pwa-forge-<id>.desktop`
- Examples:
  - `pwa-forge-chatgpt-dnai.desktop`
  - `pwa-forge-gmail.desktop`

**Rationale:**
- Prefix prevents conflicts with system apps
- ID ensures uniqueness
- Easy to identify pwa-forge-managed apps

### Wrapper Script Location

**User Mode:**
- Directory: `~/.local/bin/pwa-forge-wrappers/`
- Script name: `<id>` (no extension)
- Must be in PATH or use absolute path in .desktop

**System Mode:**
- Directory: `/usr/local/bin/pwa-forge-wrappers/`
- Requires sudo for creation

**Permissions:**
- Owner: current user (user mode) or root (system mode)
- Mode: `0755` (rwxr-xr-x)

### Profile Directory Structure

```
~/.config/pwa-forge/apps/<id>/
├── profile/              # Browser user data
│   ├── Default/
│   ├── Local State
│   └── ...
└── cache/               # Optional cache directory
```

**Isolation:**
- Each PWA has completely separate profile
- No cookies, history, or extensions shared
- Can specify custom profile location via `--profile`

### Icon Handling

**Supported Formats:**
- SVG (preferred)
- PNG (256x256 or larger)
- ICO (converted to PNG)

**Storage Location:**
- `~/.local/share/icons/pwa-forge/<id>.{svg,png}`

**Fallback Strategy:**
1. Use icon from `--icon PATH` if provided
2. Attempt to fetch from `<url>/favicon.ico`
3. Attempt to parse web manifest for icon URLs
4. Use default pwa-forge icon

**Icon Installation:**
```python
def install_icon(source: str, app_id: str, icons_dir: Path) -> Path:
    """
    Copy or download icon to pwa-forge icons directory.

    Args:
        source: Path to icon file or URL
        app_id: Application ID
        icons_dir: Target directory for icons

    Returns:
        Path to installed icon

    Raises:
        ValueError: If source is invalid or icon format unsupported
    """
    # Implementation details
```

### Browser Flag Management

**Chrome/Chromium Flags:**

*Essential for PWA:*
- `--app=<url>` - Launch as standalone app
- `--user-data-dir=<path>` - Isolated profile
- `--class=<name>` - Window manager class

*Recommended for link handling:*
- `--disable-features=IntentPickerPWALinks` - Prevent Chrome's PWA link capturing
- `--disable-features=DesktopPWAsStayInWindow` - Allow links to leave app window

*Optional cosmetic:*
- `--enable-features=WebUIDarkMode` - Dark mode UI
- `--force-dark-mode` - Force dark mode for all content
- `--ozone-platform=x11` - Specify display server (x11/wayland)

**Firefox Flags (if supporting Firefox SSB):**
- `--new-instance` - New Firefox instance
- `--profile <path>` - Custom profile
- `-kiosk <url>` - Kiosk mode (fullscreen, no chrome)

**Flag Validation:**
```python
KNOWN_CHROME_FLAGS = {
    'enable-features': 'comma-separated list',
    'disable-features': 'comma-separated list',
    'ozone-platform': ['x11', 'wayland', 'auto'],
    'force-dark-mode': 'boolean',
    'class': 'string',
    # ... more flags
}

def validate_flags(flags: Dict[str, Any]) -> List[str]:
    """Validate and format Chrome flags."""
    # Return list of formatted flag strings
```

### StartupWMClass Generation

**Rules:**
- Should match `--class` flag value
- CamelCase preferred for consistency
- Must be unique per PWA
- Used by window managers for grouping/theming

**Auto-generation:**
```python
def generate_wm_class(app_name: str) -> str:
    """
    Generate StartupWMClass from app name.

    Examples:
        "ChatGPT-DNAI" -> "ChatGPTDnai"
        "my app" -> "MyApp"
        "GMail" -> "Gmail"
    """
    # Remove special chars, title case words, join
    words = re.findall(r'\w+', app_name)
    return ''.join(word.capitalize() for word in words)
```

### Manifest Schema Validation

**JSON Schema for manifest.yaml:**
```yaml
# Schema definition
type: object
required: [id, name, url, browser]
properties:
  id:
    type: string
    pattern: "^[a-z0-9][a-z0-9_-]{0,63}$"
  name:
    type: string
    minLength: 1
    maxLength: 100
  url:
    type: string
    format: uri
    pattern: "^https?://"
  browser:
    type: string
    enum: [chrome, chromium, firefox, edge]
  profile:
    type: string
  icon:
    type: string
  comment:
    type: string
    maxLength: 200
  wm_class:
    type: string
    pattern: "^[A-Z][A-Za-z0-9]*$"
  categories:
    type: array
    items:
      type: string
      enum: [Network, WebBrowser, Utility, Office, Development, ...]
  flags:
    type: object
    properties:
      ozone_platform:
        enum: [x11, wayland, auto]
      enable_features:
        type: array
        items: {type: string}
      disable_features:
        type: array
        items: {type: string}
  out_of_scope:
    enum: [open-in-default, same-browser-window, same-browser-new-window]
  inject:
    type: object
    properties:
      userscript:
        type: string
      userscript_scheme:
        type: string
        pattern: "^[a-z][a-z0-9-]*$"
  created:
    type: string
    format: date-time
  modified:
    type: string
    format: date-time
  version:
    type: integer
    minimum: 1
```

**Validation Implementation:**
```python
import yaml
from jsonschema import validate, ValidationError

def validate_manifest(manifest_path: Path) -> Dict[str, Any]:
    """
    Load and validate manifest file.

    Returns:
        Validated manifest as dictionary

    Raises:
        ValidationError: If manifest is invalid
        FileNotFoundError: If manifest file doesn't exist
    """
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    validate(instance=manifest, schema=MANIFEST_SCHEMA)
    return manifest
```

### XDG Integration Details

**Required XDG Operations:**

1. **Desktop File Registration:**
   ```bash
   update-desktop-database ~/.local/share/applications
   ```

2. **MIME Type Registration:**
   ```bash
   xdg-mime default pwa-forge-handler-ff.desktop x-scheme-handler/ff
   ```

3. **MIME Type Query:**
   ```bash
   xdg-mime query default x-scheme-handler/ff
   ```

4. **Icon Cache Update (optional):**
   ```bash
   gtk-update-icon-cache ~/.local/share/icons/pwa-forge
   ```

**Python Wrapper:**
```python
import subprocess
from pathlib import Path

class XDGManager:
    @staticmethod
    def update_desktop_database(directory: Path) -> bool:
        """Run update-desktop-database."""
        try:
            subprocess.run(
                ['update-desktop-database', str(directory)],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update desktop database: {e.stderr}")
            return False

    @staticmethod
    def set_mime_handler(mime_type: str, desktop_file: str) -> bool:
        """Register MIME type handler."""
        try:
            subprocess.run(
                ['xdg-mime', 'default', desktop_file, mime_type],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def get_mime_handler(mime_type: str) -> str:
        """Query current handler for MIME type."""
        try:
            result = subprocess.run(
                ['xdg-mime', 'query', 'default', mime_type],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ''
```

### Browser Detection

**Detection Strategy:**
```python
class BrowserDetector:
    BROWSER_PATHS = {
        'chrome': [
            '/usr/bin/google-chrome-stable',
            '/usr/bin/google-chrome',
            '/snap/bin/chromium',
        ],
        'chromium': [
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
        ],
        'firefox': [
            '/usr/bin/firefox',
            '/snap/bin/firefox',
        ],
        'edge': [
            '/usr/bin/microsoft-edge-stable',
            '/usr/bin/microsoft-edge',
        ],
    }

    @classmethod
    def find_browser(cls, browser_name: str) -> Optional[Path]:
        """
        Find browser executable.

        Returns:
            Path to browser or None if not found
        """
        # First check config
        config_path = Config.get_browser_path(browser_name)
        if config_path and Path(config_path).exists():
            return Path(config_path)

        # Then check known paths
        for path_str in cls.BROWSER_PATHS.get(browser_name, []):
            path = Path(path_str)
            if path.exists() and path.is_file():
                return path

        # Finally try which/where
        try:
            result = subprocess.run(
                ['which', browser_name],
                capture_output=True,
                text=True,
                check=True
            )
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            return None

    @classmethod
    def detect_all(cls) -> Dict[str, Path]:
        """Detect all available browsers."""
        found = {}
        for browser in cls.BROWSER_PATHS.keys():
            path = cls.find_browser(browser)
            if path:
                found[browser] = path
        return found
```

### Dry-Run Mode Implementation

**Strategy:**
- All file operations should be wrapped in functions that respect dry-run flag
- Print what would be done instead of doing it
- Use distinctive formatting (e.g., color, prefix)

**Example:**
```python
class FileOperations:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def write_file(self, path: Path, content: str) -> bool:
        """Write file or simulate if dry-run."""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would write to {path}")
            logger.debug(f"[DRY-RUN] Content:\n{content}")
            return True

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            logger.info(f"Wrote {path}")
            return True
        except IOError as e:
            logger.error(f"Failed to write {path}: {e}")
            return False

    def remove_file(self, path: Path) -> bool:
        """Remove file or simulate if dry-run."""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would remove {path}")
            return True

        try:
            if path.exists():
                path.unlink()
                logger.info(f"Removed {path}")
            return True
        except IOError as e:
            logger.error(f"Failed to remove {path}: {e}")
            return False
```

### Userscript Installation Instructions

**Since userscripts cannot be auto-installed in Chrome profiles, provide clear instructions:**

```python
def print_userscript_instructions(app_id: str, userscript_path: Path):
    """Print instructions for installing userscript."""
    print(f"""
╭─────────────────────────────────────────────────────────╮
│  Userscript Installation Required                      │
╰─────────────────────────────────────────────────────────╯

To enable external link redirection for '{app_id}', you need to:

1. Install a userscript manager in your PWA profile:

   • Open the PWA: pwa-forge launch {app_id}
   • Navigate to Chrome Web Store
   • Install "Violentmonkey" or "Tampermonkey"

2. Install the generated userscript:

   • Open Violentmonkey/Tampermonkey dashboard
   • Click "+ " or "Create new script"
   • Copy the content from: {userscript_path}
   • Save the script

3. Test external link redirection:

   • Click an external link in the PWA
   • It should open in your system browser (Firefox)

Alternative: Use --browser firefox for native SSB support (if available)

For more help: pwa-forge help userscripts
""")
```

### Concurrent Access Handling

**Registry File Locking:**
```python
import fcntl
import json
from contextlib import contextmanager

class Registry:
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path

    @contextmanager
    def _lock(self):
        """Acquire exclusive lock on registry file."""
        lock_path = self.registry_path.with_suffix('.lock')
        lock_file = open(lock_path, 'w')
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()

    def read(self) -> Dict:
        """Read registry with lock."""
        with self._lock():
            if not self.registry_path.exists():
                return {'version': 1, 'apps': [], 'handlers': []}
            return json.loads(self.registry_path.read_text())

    def write(self, data: Dict):
        """Write registry with lock."""
        with self._lock():
            self.registry_path.write_text(json.dumps(data, indent=2))
```

### URL Validation

**Requirements:**
- Must be valid HTTP or HTTPS URL
- Must be reachable (optional check with --verify)
- Warn about localhost URLs (won't work from launcher)

```python
import requests
from urllib.parse import urlparse

def validate_url(url: str, verify: bool = False) -> tuple[bool, str]:
    """
    Validate URL format and optionally check accessibility.

    Returns:
        (is_valid, message)
    """
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    # Check scheme
    if parsed.scheme not in ('http', 'https'):
        return False, "URL must use http:// or https://"

    # Check host
    if not parsed.netloc:
        return False, "URL must include a hostname"

    # Warn about localhost
    if parsed.netloc in ('localhost', '127.0.0.1', '::1'):
        return True, "Warning: localhost URLs won't work from system launcher"

    # Optional connectivity check
    if verify:
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code >= 400:
                return False, f"URL returned HTTP {response.status_code}"
        except requests.RequestException as e:
            return False, f"URL not accessible: {e}"

    return True, "OK"
```

### Color Output

**Use click's styling for consistent colorized output:**

```python
import click

def success(message: str):
    """Print success message in green."""
    click.secho(f"✓ {message}", fg='green')

def error(message: str):
    """Print error message in red."""
    click.secho(f"✗ {message}", fg='red', err=True)

def warning(message: str):
    """Print warning in yellow."""
    click.secho(f"⚠ {message}", fg='yellow')

def info(message: str):
    """Print info message."""
    click.echo(f"ℹ {message}")

def header(message: str):
    """Print section header."""
    click.secho(f"\n{'─' * 60}", fg='blue')
    click.secho(f"  {message}", fg='blue', bold=True)
    click.secho(f"{'─' * 60}", fg='blue')
```

**Respect NO_COLOR environment variable:**
```python
import os

def should_use_color() -> bool:
    """Check if color output should be used."""
    return (
        not os.environ.get('NO_COLOR') and
        sys.stdout.isatty()
    )
```

---

## Example Usage Scenarios

### Scenario 1: Simple PWA Creation
```bash
# Create ChatGPT PWA with defaults
$ pwa-forge add https://chat.openai.com --name "ChatGPT"

✓ Validating URL...
✓ Creating profile directory...
✓ Generating wrapper script...
✓ Creating desktop file...
✓ Registering with system...

PWA 'ChatGPT' (chatgpt) created successfully!

Launch from your application menu or run:
  pwa-forge launch chatgpt
```

### Scenario 2: Advanced Configuration
```bash
# Create with custom settings and external link handling
$ pwa-forge add https://mail.google.com \
    --name "Gmail" \
    --id gmail-work \
    --profile ~/.config/work-apps/gmail \
    --icon ~/Pictures/gmail-icon.svg \
    --wm-class GmailWork \
    --out-of-scope open-in-default \
    --chrome-flags "--force-dark-mode"

# Generate and install handler for external links
$ pwa-forge generate-handler --scheme ff --browser firefox
$ pwa-forge install-handler --scheme ff

# Generate userscript
$ pwa-forge generate-userscript \
    --scheme ff \
    --in-scope-hosts mail.google.com,accounts.google.com \
    --out ~/.local/share/pwa-forge/apps/gmail-work/userscripts/external-links.user.js

# Follow instructions to install userscript in PWA
```

### Scenario 3: Auditing and Troubleshooting
```bash
# List all PWAs
$ pwa-forge list
ID              Name            URL                           Status
──────────────────────────────────────────────────────────────────────
chatgpt         ChatGPT         https://chat.openai.com       active
gmail-work      Gmail           https://mail.google.com       active
jira-project    Jira            https://company.atlassian...  broken

# Audit specific PWA
$ pwa-forge audit jira-project

Auditing PWA: jira-project
─────────────────────────────
✓ Manifest file exists
✓ Desktop file exists
✗ Wrapper script missing
✓ Profile directory exists
✓ Browser executable found
✗ StartupWMClass mismatch (expected: JiraProject, found: Jira)

2 issues found. Run with --fix to attempt repairs.

# Fix issues
$ pwa-forge audit jira-project --fix

Repairing PWA: jira-project
─────────────────────────────
✓ Regenerated wrapper script
✓ Updated desktop file with correct WMClass

All issues resolved!
```

### Scenario 4: Managing Multiple PWAs
```bash
# Create multiple instances of same service
$ pwa-forge add https://github.com --name "GitHub Personal" --id github-personal
$ pwa-forge add https://github.com --name "GitHub Work" --id github-work \
    --profile ~/.config/work-profiles/github

# List with verbose output
$ pwa-forge list --verbose --format json > pwa-inventory.json

# Remove old PWA
$ pwa-forge remove old-app --remove-profile
```

### Scenario 5: Configuration Management
```bash
# View current config
$ pwa-forge config list

default_browser: chrome
chrome_exec: /usr/bin/google-chrome-stable
...

# Change default browser
$ pwa-forge config set default_browser firefox

# Edit config file directly
$ pwa-forge config edit

# Reset to defaults
$ pwa-forge config reset
```

---

## CLI Help Text Examples

### Main Help
```
$ pwa-forge --help

Usage: pwa-forge [OPTIONS] COMMAND [ARGS]...

  PWA Forge - Manage Progressive Web Apps as standalone applications

  PWA Forge creates isolated browser instances for web apps with custom
  launchers, proper desktop integration, and external link redirection.

Options:
  --version              Show version and exit
  --config PATH          Config file path [default: ~/.config/pwa-forge/config.yaml]
  --verbose, -v          Verbose output (can be repeated: -vv, -vvv)
  --quiet, -q            Suppress non-error output
  --dry-run              Show what would be done without making changes
  --no-color             Disable colored output
  --help                 Show this message and exit

Commands:
  add                Create a new PWA
  remove             Remove a PWA
  list               List managed PWAs
  audit              Validate PWA configuration
  sync               Regenerate PWA artifacts from manifest
  edit               Edit PWA manifest
  launch             Launch a PWA
  generate-handler   Generate URL scheme handler script
  install-handler    Install URL scheme handler
  generate-userscript Generate external link userscript
  config             Manage configuration
  template           Show file templates
  scaffold           Create skeleton PWA configuration
  doctor             Check system requirements

Examples:
  # Create a simple PWA
  pwa-forge add https://chat.openai.com --name "ChatGPT"

  # Create with external link handling
  pwa-forge add https://mail.google.com --name Gmail --out-of-scope open-in-default
  pwa-forge generate-handler --scheme ff --browser firefox
  pwa-forge install-handler --scheme ff

  # List and audit
  pwa-forge list --verbose
  pwa-forge audit chatgpt --fix

  For more help: https://github.com/bigr/pwa_forge
```

### Add Command Help
```
$ pwa-forge add --help

Usage: pwa-forge add [OPTIONS] URL

  Create a new Progressive Web App

  Creates an isolated browser instance with custom launcher and desktop
  integration. Optionally configures external link redirection.

Arguments:
  URL  Web application URL (must be http:// or https://)

Options:
  --name TEXT                Display name [default: from URL]
  --id TEXT                  Unique identifier [default: generated from name]
  --browser [chrome|chromium|firefox|edge]
                            Browser engine [default: from config]
  --profile PATH            Custom profile directory [default: auto]
  --icon PATH               Application icon path
  --wm-class TEXT           Window manager class [default: auto]
  --out-of-scope [open-in-default|same-browser-window|same-browser-new-window]
                            External link behavior [default: from config]
  --inject-userscript PATH  Custom userscript for link interception
  --chrome-flags TEXT       Additional Chrome flags (e.g. "--force-dark-mode")
  --verify                  Check URL accessibility before creating
  --dry-run                 Show what would be created
  --help                    Show this message and exit

Examples:
  # Simple creation
  pwa-forge add https://chat.openai.com --name "ChatGPT"

  # With custom profile and icon
  pwa-forge add https://app.slack.com/client \
      --name "Slack" \
      --profile ~/.config/slack-pwa \
      --icon ~/Pictures/slack.svg

  # With external link handling
  pwa-forge add https://mail.google.com \
      --name Gmail \
      --out-of-scope open-in-default \
      --inject-userscript ~/.local/share/pwa-forge/userscripts/gmail-links.user.js
```

---

This completes the comprehensive implementation specification for **pwa-forge**. The specification includes:

1. ✅ Complete functional requirements for all commands
2. ✅ Detailed configuration file formats
3. ✅ File templates for all generated artifacts
4. ✅ Architecture and module structure
5. ✅ Implementation phases and milestones
6. ✅ Technical specifications for all components
7. ✅ Security considerations
8. ✅ Testing requirements
9. ✅ Documentation requirements
10. ✅ Example usage scenarios
11. ✅ CLI help text examples
