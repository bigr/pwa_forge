# PWA Forge Usage Guide

Complete guide to using PWA Forge for managing Progressive Web Apps on Linux.

## Table of Contents

- [Quick Start](#quick-start)
- [Core Commands](#core-commands)
  - [add - Create a PWA](#add---create-a-pwa)
  - [list - List PWAs](#list---list-pwas)
  - [remove - Remove a PWA](#remove---remove-a-pwa)
  - [audit - Validate PWAs](#audit---validate-pwas)
  - [sync - Regenerate Artifacts](#sync---regenerate-artifacts)
  - [edit - Edit Manifest](#edit---edit-manifest)
- [URL Handler System](#url-handler-system)
  - [generate-handler](#generate-handler)
  - [install-handler](#install-handler)
  - [generate-userscript](#generate-userscript)
- [Configuration Management](#configuration-management)
- [Advanced Usage](#advanced-usage)
- [Examples](#examples)

## Quick Start

### Installation

**Note:** PWA Forge is not yet published to PyPI. Please install from source:

```bash
# Install from source
git clone https://github.com/bigr/pwa_forge.git
cd pwa_forge
pip install -e .

# Or install directly via pip with git
pip install git+https://github.com/bigr/pwa_forge.git
```

### Create Your First PWA

```bash
# Simple creation
pwa-forge add https://chat.openai.com --name "ChatGPT"

# The PWA will appear in your application menu
# Launch it like any other application
```

### Verify Installation

```bash
# List all PWAs
pwa-forge list

# Check system requirements
pwa-forge doctor
```

## Core Commands

### add - Create a PWA

Create a new Progressive Web App with isolated browser profile.

```bash
pwa-forge add <url> [OPTIONS]
```

#### Required Arguments

- `<url>` - The web application URL (must be http:// or https://)

#### Options

- `--name TEXT` - Display name for the application (default: extracted from URL)
- `--id TEXT` - Unique identifier (default: generated from name)
- `--browser {chrome|chromium|firefox|edge}` - Browser engine to use (default: chrome)
- `--profile PATH` - Custom profile directory (default: auto-generated)
- `--icon PATH` - Path to application icon (default: uses favicon)
- `--wm-class TEXT` - Window manager class for desktop integration (default: auto-generated)
- `--out-of-scope {open-in-default|same-browser-window|same-browser-new-window}` - External link behavior
- `--inject-userscript PATH` - Custom userscript for link interception
- `--chrome-flags TEXT` - Additional Chrome/Chromium flags
- `--verify` - Check URL accessibility before creating
- `--dry-run` - Show what would be created without making changes

#### Examples

**Simple PWA:**

```bash
pwa-forge add https://chat.openai.com --name "ChatGPT"
```

**With custom profile and icon:**

```bash
pwa-forge add https://app.slack.com/client \
  --name "Slack" \
  --profile ~/.config/slack-pwa \
  --icon ~/Pictures/slack.svg
```

**With external link handling:**

```bash
pwa-forge add https://mail.google.com \
  --name "Gmail" \
  --out-of-scope open-in-default
```

**Multiple instances of same service:**

```bash
pwa-forge add https://github.com --name "GitHub Personal" --id github-personal
pwa-forge add https://github.com --name "GitHub Work" --id github-work \
  --profile ~/.config/work-profiles/github
```

**With custom Chrome flags:**

```bash
pwa-forge add https://example.com \
  --name "Dark App" \
  --chrome-flags "--force-dark-mode --enable-features=WebUIDarkMode"
```

**Dry run to preview:**

```bash
pwa-forge add https://example.com --name "Test" --dry-run
```

#### What Gets Created

When you create a PWA, pwa-forge generates:

1. **Profile Directory**: `~/.config/pwa-forge/apps/<id>/`
   - Isolated browser profile with separate cookies, history, and extensions

2. **Wrapper Script**: `~/.local/bin/pwa-forge-wrappers/<id>`
   - Executable script that launches the browser with correct flags

3. **Desktop File**: `~/.local/share/applications/pwa-forge-<id>.desktop`
   - Makes the PWA appear in your application menu

4. **Manifest**: `~/.local/share/pwa-forge/apps/<id>/manifest.yaml`
   - Stores configuration for the PWA

5. **Registry Entry**: `~/.local/share/pwa-forge/registry.json`
   - Tracks all managed PWAs

### list - List PWAs

Display all managed PWA instances.

```bash
pwa-forge list [OPTIONS]
```

#### Options

- `--verbose`, `-v` - Show detailed information
- `--format {table|json|yaml}` - Output format (default: table)

#### Examples

**Compact table view:**

```bash
pwa-forge list
```

Output:
```
ID                   Name                     URL                                      Status
----------------------------------------------------------------------------------------
chatgpt              ChatGPT                  https://chat.openai.com                  active
gmail-work           Gmail                    https://mail.google.com                  active
slack                Slack                    https://app.slack.com/client             active
```

**Verbose output:**

```bash
pwa-forge list --verbose
```

Output:
```
ID: chatgpt
  Name: ChatGPT
  URL: https://chat.openai.com
  Status: active
  Desktop File: ~/.local/share/applications/pwa-forge-chatgpt.desktop
  Wrapper Script: ~/.local/bin/pwa-forge-wrappers/chatgpt
  Manifest: ~/.local/share/pwa-forge/apps/chatgpt/manifest.yaml

...
```

**JSON format:**

```bash
pwa-forge list --format json > pwa-inventory.json
```

**YAML format:**

```bash
pwa-forge list --format yaml
```

### remove - Remove a PWA

Remove a PWA instance and optionally clean up user data.

```bash
pwa-forge remove <id> [OPTIONS]
```

#### Required Arguments

- `<id>` - Application ID or name

#### Options

- `--remove-profile` - Also delete the browser profile directory
- `--remove-icon` - Also delete the icon file
- `--keep-userdata` - Keep browser profile but remove launcher
- `--dry-run` - Show what would be removed without making changes

#### Examples

**Remove launcher only (keep profile data):**

```bash
pwa-forge remove chatgpt
```

**Remove everything including profile:**

```bash
pwa-forge remove chatgpt --remove-profile
```

**Remove launcher but explicitly keep user data:**

```bash
pwa-forge remove old-app --keep-userdata
```

**Preview what will be removed:**

```bash
pwa-forge remove chatgpt --remove-profile --dry-run
```

#### What Gets Removed

By default (without `--remove-profile`):
- Desktop file
- Wrapper script
- Manifest file
- Registry entry

**Profile directory is preserved** (contains cookies, history, cache)

With `--remove-profile`:
- All of the above
- Browser profile directory and all user data

With `--remove-icon`:
- Icon file (if not shared)

### audit - Validate PWAs

Validate PWA configuration and detect issues.

```bash
pwa-forge audit [id] [OPTIONS]
```

#### Arguments

- `<id>` - Application ID or name (omit to audit all PWAs)

#### Options

- `--fix` - Attempt to repair broken configurations
- `--open-test-page` - Launch PWA with test page to verify link handling (not yet implemented)

#### Checks Performed

1. **Manifest file exists** - Checks if the manifest.yaml file is present
2. **Manifest valid YAML** - Validates YAML syntax
3. **Desktop file exists** - Checks if .desktop file is present
4. **Desktop file valid** - Validates desktop file format
5. **Wrapper script exists** - Checks if wrapper script is present
6. **Wrapper script executable** - Verifies execute permissions
7. **Profile directory exists** - Checks if browser profile directory exists
8. **Browser executable exists** - Verifies browser is installed
9. **Icon exists** - Checks if icon file is present (if configured)

#### Examples

**Audit specific PWA:**

```bash
pwa-forge audit chatgpt
```

Output:
```
Auditing PWA: chatgpt
─────────────────────────────
✓ Manifest file exists
✓ Desktop file exists
✓ Wrapper script exists
✓ Wrapper script executable
✓ Profile directory exists
✓ Browser executable found: /usr/bin/google-chrome-stable
✓ Icon file exists

All checks passed!
```

**Audit all PWAs:**

```bash
pwa-forge audit
```

**Audit with automatic fix:**

```bash
pwa-forge audit chatgpt --fix
```

Output:
```
Auditing PWA: chatgpt
─────────────────────────────
✓ Manifest file exists
✗ Wrapper script missing

Repairing issues...
✓ Regenerated wrapper script
✓ Set correct permissions

All issues resolved!
```

**Common Issues Detected:**

- Missing or corrupted wrapper scripts
- Missing desktop files
- Incorrect file permissions
- Missing browser executables
- Broken manifest files
- Missing profile directories

### sync - Regenerate Artifacts

Regenerate wrapper script and desktop file from manifest.

```bash
pwa-forge sync <id> [OPTIONS]
```

#### Required Arguments

- `<id>` - Application ID or name

#### Options

- `--dry-run` - Show what would be regenerated without making changes

#### When to Use Sync

Use `sync` after:
- Manually editing the manifest file
- Updating browser paths or flags
- Fixing corrupted wrapper scripts or desktop files
- Changing PWA configuration

#### Examples

**Regenerate all artifacts:**

```bash
pwa-forge sync chatgpt
```

**Preview changes:**

```bash
pwa-forge sync chatgpt --dry-run
```

**Workflow: Edit manifest then sync:**

```bash
# Edit manifest
pwa-forge edit chatgpt

# Make changes in $EDITOR, save and exit

# Artifacts are automatically regenerated
# Or manually sync if auto-sync was disabled:
pwa-forge sync chatgpt
```

#### What Gets Regenerated

- Wrapper script (with updated flags, browser path, URL)
- Desktop file (with updated name, icon, categories)
- Manifest timestamp (updated to current time)

**Note:** Profile directory and user data are never modified.

### edit - Edit Manifest

Open the PWA manifest file in your text editor.

```bash
pwa-forge edit <id> [OPTIONS]
```

#### Required Arguments

- `<id>` - Application ID or name

#### Options

- `--no-sync` - Skip automatic sync after editing

#### Prerequisites

Set your preferred editor:
```bash
export EDITOR=vim  # or nano, emacs, code, etc.
```

#### Examples

**Edit and auto-sync:**

```bash
pwa-forge edit chatgpt
```

**Edit without auto-sync:**

```bash
pwa-forge edit chatgpt --no-sync
# Manually sync later if needed:
pwa-forge sync chatgpt
```

#### Editing Workflow

1. Command opens manifest in `$EDITOR`
2. Make changes and save
3. Manifest is validated on save
4. If valid and auto-sync enabled, artifacts are regenerated
5. If invalid, backup is restored and errors are shown

#### Common Edits

**Change browser flags:**

```yaml
flags:
  ozone_platform: x11
  enable_features:
    - WebUIDarkMode
    - TouchpadOverscrollHistoryNavigation
  disable_features:
    - IntentPickerPWALinks
```

**Update URL:**

```yaml
url: https://new-domain.example.com
```

**Change window manager class:**

```yaml
wm_class: CustomWMClass
```

**Add categories:**

```yaml
categories:
  - Network
  - WebBrowser
  - Office
```

## URL Handler System

The URL handler system allows external links in PWAs to open in your system browser.

### Complete Setup Example

```bash
# Step 1: Create PWA with external link handling
pwa-forge add https://mail.google.com \
  --name "Gmail" \
  --out-of-scope open-in-default

# Step 2: Generate URL handler script
pwa-forge generate-handler --scheme ff --browser firefox

# Step 3: Install handler (register with system)
pwa-forge install-handler --scheme ff

# Step 4: Generate userscript
pwa-forge generate-userscript \
  --scheme ff \
  --in-scope-hosts mail.google.com,accounts.google.com \
  --out ~/.local/share/pwa-forge/userscripts/gmail-links.user.js

# Step 5: Install userscript in PWA
# Launch the PWA and install Violentmonkey/Tampermonkey
# Then install the generated userscript
```

### generate-handler

Generate a URL scheme handler script.

```bash
pwa-forge generate-handler --scheme <scheme> [OPTIONS]
```

#### Required Options

- `--scheme SCHEME` - URL scheme to handle (e.g., "ff" for ff:// URLs)

#### Optional Options

- `--browser {firefox|chrome|chromium|edge}` - Browser to open URLs in (default: firefox)
- `--out PATH` - Output path for handler script (default: ~/.local/bin/pwa-forge-handler-<scheme>)

#### Examples

```bash
# Generate handler for ff:// scheme
pwa-forge generate-handler --scheme ff --browser firefox

# Custom output path
pwa-forge generate-handler --scheme ff --out ~/bin/my-handler
```

### install-handler

Register a URL scheme handler with the system.

```bash
pwa-forge install-handler --scheme <scheme> [OPTIONS]
```

#### Required Options

- `--scheme SCHEME` - URL scheme to register

#### Optional Options

- `--handler-script PATH` - Path to handler script (default: auto-detected)

#### Examples

```bash
# Install handler (uses auto-detected script)
pwa-forge install-handler --scheme ff

# Install with custom handler script path
pwa-forge install-handler --scheme ff \
  --handler-script ~/bin/my-handler
```

### generate-userscript

Generate a userscript for external link interception.

```bash
pwa-forge generate-userscript [OPTIONS]
```

#### Optional Options

- `--scheme SCHEME` - URL scheme to redirect to (default: ff)
- `--in-scope-hosts HOSTS` - Comma-separated list of hosts to keep in-app
- `--out PATH` - Output path for userscript

#### Examples

```bash
# Generate for Gmail
pwa-forge generate-userscript \
  --scheme ff \
  --in-scope-hosts mail.google.com,accounts.google.com \
  --out ~/.local/share/pwa-forge/userscripts/gmail.user.js

# Generate for Slack
pwa-forge generate-userscript \
  --scheme ff \
  --in-scope-hosts app.slack.com,slack.com \
  --out ~/.local/share/pwa-forge/userscripts/slack.user.js
```

#### Installing the Userscript

1. Launch your PWA
2. Install Violentmonkey or Tampermonkey extension
3. Open the extension dashboard
4. Click "Create new script" or "+"
5. Copy content from the generated userscript file
6. Save the script

## Configuration Management

### config get

Display a configuration value.

```bash
pwa-forge config get <key>
```

**Examples:**

```bash
# Get default browser
pwa-forge config get default_browser

# Get Chrome path
pwa-forge config get browsers.chrome

# Get log level
pwa-forge config get log_level
```

### config set

Set a configuration value.

```bash
pwa-forge config set <key> <value>
```

**Examples:**

```bash
# Change default browser
pwa-forge config set default_browser firefox

# Update browser path
pwa-forge config set browsers.chrome /usr/bin/google-chrome-stable

# Change log level
pwa-forge config set log_level debug
```

### config list

Show all configuration values.

```bash
pwa-forge config list
```

### config reset

Reset configuration to defaults.

```bash
pwa-forge config reset
```

### config edit

Open configuration file in `$EDITOR`.

```bash
pwa-forge config edit
```

## Advanced Usage

### Custom Browser Profiles

Use separate profiles for work and personal accounts:

```bash
# Work profile
pwa-forge add https://mail.google.com \
  --name "Gmail Work" \
  --id gmail-work \
  --profile ~/.config/work-profiles/gmail

# Personal profile
pwa-forge add https://mail.google.com \
  --name "Gmail Personal" \
  --id gmail-personal \
  --profile ~/.config/personal-profiles/gmail
```

### Custom Chrome Flags

#### Dark Mode

```bash
pwa-forge add https://example.com \
  --chrome-flags "--force-dark-mode --enable-features=WebUIDarkMode"
```

#### Wayland Support

```bash
pwa-forge add https://example.com \
  --chrome-flags "--ozone-platform=wayland"
```

#### Disable Features

```bash
pwa-forge add https://example.com \
  --chrome-flags "--disable-features=IntentPickerPWALinks,DesktopPWAsStayInWindow"
```

### Window Manager Integration

Custom WM classes for window rules:

```bash
pwa-forge add https://app.slack.com \
  --name "Slack" \
  --wm-class SlackWorkspace
```

Then in KDE/Plasma, create window rules for `SlackWorkspace`.

### Backup and Restore

#### Backup PWAs

```bash
# Export list of PWAs
pwa-forge list --format json > ~/backups/pwa-list.json

# Backup profile data
cp -r ~/.config/pwa-forge/apps ~/backups/pwa-profiles
cp -r ~/.local/share/pwa-forge ~/backups/pwa-data
```

#### Restore PWAs

Manually recreate PWAs from the JSON list, or copy back the profile directories and use `pwa-forge add` with the same IDs.

### Scripting with PWA Forge

#### Bulk Operations

```bash
#!/bin/bash
# Install multiple PWAs

declare -A pwas=(
  ["chatgpt"]="https://chat.openai.com"
  ["gmail"]="https://mail.google.com"
  ["slack"]="https://app.slack.com/client"
)

for id in "${!pwas[@]}"; do
  url="${pwas[$id]}"
  pwa-forge add "$url" --id "$id" --name "${id^}"
done
```

#### Health Check

```bash
#!/bin/bash
# Audit all PWAs and fix issues

pwa-forge list --format json | jq -r '.[].id' | while read id; do
  echo "Auditing: $id"
  pwa-forge audit "$id" --fix
done
```

## Examples

### Example 1: ChatGPT with Dark Mode

```bash
pwa-forge add https://chat.openai.com \
  --name "ChatGPT" \
  --chrome-flags "--force-dark-mode --enable-features=WebUIDarkMode"
```

### Example 2: Multiple GitHub Accounts

```bash
# Personal account
pwa-forge add https://github.com \
  --name "GitHub Personal" \
  --id github-personal \
  --icon ~/Pictures/github-personal.svg

# Work account
pwa-forge add https://github.com \
  --name "GitHub Work" \
  --id github-work \
  --profile ~/.config/work/github \
  --icon ~/Pictures/github-work.svg \
  --wm-class GitHubWork
```

### Example 3: Gmail with External Link Handling

```bash
# Create PWA
pwa-forge add https://mail.google.com \
  --name "Gmail" \
  --out-of-scope open-in-default

# Setup URL handler
pwa-forge generate-handler --scheme gmail --browser firefox
pwa-forge install-handler --scheme gmail

# Generate and install userscript
pwa-forge generate-userscript \
  --scheme gmail \
  --in-scope-hosts mail.google.com,accounts.google.com \
  --out ~/.local/share/pwa-forge/userscripts/gmail.user.js

# Then install the userscript in Gmail PWA using Violentmonkey
```

### Example 4: Wayland Native Application

```bash
pwa-forge add https://app.example.com \
  --name "Example App" \
  --chrome-flags "--ozone-platform=wayland --enable-features=UseOzonePlatform"
```

### Example 5: Maintenance and Cleanup

```bash
# List all PWAs
pwa-forge list --verbose

# Audit and fix issues
pwa-forge audit --fix

# Remove unused PWA
pwa-forge remove old-app --remove-profile

# Update desktop database manually if needed
update-desktop-database ~/.local/share/applications
```

## See Also

- [README.md](../README.md) - Quick start and installation
- [TESTING.md](TESTING.md) - Running tests and development
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
