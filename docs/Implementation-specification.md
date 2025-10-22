# Implementation Specification: PWA Forge

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

#### From PyPI
```bash
pip install pwa-forge
```

#### From Source
```bash
git clone https://github.com/yourusername/pwa-forge.git
cd pwa-forge
pip install -e .
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

### Phase 1: Core Infrastructure
- [X] Project scaffolding and package structure
- [X] CLI framework (Click) with basic commands
- [X] Configuration system (YAML loading)
- [X] Template engine (Jinja2) with basic templates
- [X] Logging setup
- [X] Path utilities

### Phase 2: Basic PWA Management
- [ ] `add` command implementation
  - [X] URL validation
  - [ ] Profile directory creation
  - [ ] Wrapper script generation
  - [ ] Desktop file generation
  - [ ] Icon handling (copy from path)
  - [X] Registry entry creation
- [ ] `list` command implementation
  - [ ] Table format output
  - [ ] JSON/YAML format support
  - [ ] Verbose mode
- [ ] `remove` command implementation
  - [ ] Safe file deletion
  - [ ] Profile cleanup option
  - [ ] Registry update
- [X] Registry management
  - [X] JSON-based index
  - [X] CRUD operations
  - [X] Locking for concurrent access

### Phase 3: Browser Integration Test Framework
- [ ] Tooling setup
  - [ ] Add Playwright to project dependencies (`optional-dev` extra)
  - [ ] Provide `tox` environment for Playwright tests (headless only)
  - [ ] Document local browser driver requirements and installation steps
  - [ ] Optional: scaffold `npm` workspace with Jest + jsdom for fast JS unit tests (userscript helpers)
- [ ] Test harness
  - [ ] Create fixtures to spin up temporary test PWAs (wrapper, desktop file, userscript)
  - [ ] Implement utilities for launching Playwright in headless mode with injected userscript
  - [ ] Capture logs and screenshots on failure for CI artifacts
- [ ] Core scenarios
  - [ ] External link rewrite: confirm `userscript.j2` rewrites links to custom scheme
  - [ ] Window opening: ensure `window.open` calls use custom scheme
  - [ ] Handler integration: verify handler script receives decoded URL and launches browser stub
- [ ] CI integration
  - [ ] Run Playwright smoke suite in GitHub Actions (Linux, Chromium)
  - [ ] Allow opt-out via env flag for contributors without browsers installed
  - [ ] Publish HTML reports as build artifacts
  - [ ] Optional: run Jest unit suite in Node.js workflow for rapid feedback

### Phase 4: URL Handler System
- [ ] `generate-handler` command
  - [ ] Template rendering
  - [ ] URL decoding logic
  - [ ] Security validation
  - [ ] Multiple browser support
- [ ] `install-handler` command
  - [ ] Desktop file creation for handler
  - [ ] XDG mime registration
  - [ ] Verification of registration
- [ ] `generate-userscript` command
  - [ ] Template with configurable scheme
  - [ ] In-scope host configuration
  - [ ] Instructions for manual installation

### Phase 5: Validation & Audit
- [ ] `audit` command implementation
  - [ ] File existence checks
  - [ ] Desktop file validation
  - [ ] Wrapper script validation
  - [ ] Profile directory validation
  - [ ] Handler registration check
  - [ ] Browser executable check
  - [ ] Fix mode (--fix flag)
- [ ] `sync` command
  - [ ] Regenerate artifacts from manifest
  - [ ] Detect and warn about manual changes
- [ ] `edit` command
  - [ ] Open manifest in $EDITOR
  - [ ] Validate YAML after edit
  - [ ] Offer to sync

### Phase 6: Testing & Polish
- [ ] Unit tests
  - [ ] Template rendering tests
  - [ ] Configuration loading tests
  - [ ] Path utilities tests
  - [ ] Validation logic tests
  - [ ] Registry operations tests
- [ ] Integration tests
  - [ ] Add/list/remove cycle
  - [ ] Handler generation and registration
  - [ ] Audit with various configurations
  - [ ] Dry-run mode
- [ ] Documentation
  - [ ] README with quick start
  - [ ] USAGE guide with examples
  - [ ] Inline help text refinement
  - [ ] Troubleshooting guide
- [ ] Code quality
  - [ ] Linting with ruff
  - [ ] Type hints with mypy
  - [ ] Code formatting with black
  - [ ] 70%+ test coverage

### Phase 7: Release Preparation
- [ ] Package for PyPI
  - [ ] setup.py configuration
  - [ ] version management
  - [ ] dependencies declaration
- [ ] Shell completion scripts
  - [ ] Bash completion
  - [ ] Zsh completion
- [ ] `doctor` command
  - [ ] System requirements check
  - [ ] Dependency detection
  - [ ] Configuration validation
- [ ] Error handling polish
  - [ ] Consistent error codes
  - [ ] Actionable error messages
  - [ ] Graceful degradation
- [ ] Release notes and changelog

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

  For more help: https://github.com/yourusername/pwa-forge
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
