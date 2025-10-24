# PWA Forge Troubleshooting Guide

Solutions to common issues when using PWA Forge.

## Table of Contents

- [Installation Issues](#installation-issues)
- [PWA Creation Issues](#pwa-creation-issues)
- [Launch Issues](#launch-issues)
- [External Link Handling](#external-link-handling)
- [Desktop Integration](#desktop-integration)
- [Browser Issues](#browser-issues)
- [Profile and Data Issues](#profile-and-data-issues)
- [Permission Issues](#permission-issues)
- [Diagnostic Commands](#diagnostic-commands)

## Installation Issues

### Python Version Error

**Problem:** Error about unsupported Python version.

```
ERROR: pwa-forge requires Python>=3.10
```

**Solution:**

1. Check your Python version:
   ```bash
   python3 --version
   ```

2. Install Python 3.10 or later:
   ```bash
   # Ubuntu/Debian
   sudo add-apt-repository ppa:deadsnakes/ppa
   sudo apt update
   sudo apt install python3.10 python3.10-venv

   # Fedora
   sudo dnf install python3.10
   ```

3. Create a virtual environment with the correct version:
   ```bash
   python3.10 -m venv .venv
   source .venv/bin/activate
   pip install git+https://github.com/bigr/pwa_forge.git
   # Or for offline: export PYTHONPATH="/path/to/pwa_forge/src:$PYTHONPATH"
   ```

### Missing Dependencies

**Problem:** Import errors or missing modules.

```
ModuleNotFoundError: No module named 'click'
```

**Solution:**

Reinstall with all dependencies:
```bash
pip install --upgrade --force-reinstall pwa-forge
```

For development:
```bash
pip install -e ".[dev]"
```

## PWA Creation Issues

### Browser Executable Not Found

**Problem:** Error when creating PWA.

```
Error: Browser 'chrome' not found.
→ Install Chrome: sudo apt install google-chrome-stable
→ Or use a different browser: pwa-forge add --browser firefox <url>
```

**Solutions:**

**Option 1: Install the browser**

```bash
# Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb

# Chromium
sudo apt install chromium-browser  # Ubuntu/Debian
sudo dnf install chromium           # Fedora

# Firefox
sudo apt install firefox            # Ubuntu/Debian
sudo dnf install firefox            # Fedora
```

**Option 2: Use a different browser**

```bash
pwa-forge add https://example.com --browser firefox
```

**Option 3: Configure custom browser path**

```bash
pwa-forge config set browsers.chrome /snap/bin/chromium
```

### Invalid URL Error

**Problem:** URL validation fails.

```
Error: Invalid URL: URL must use http:// or https://
```

**Solution:**

Ensure the URL includes the protocol:
```bash
# Wrong
pwa-forge add example.com

# Correct
pwa-forge add https://example.com
```

### PWA Already Exists

**Problem:** Duplicate ID error.

```
Error: PWA with ID 'example' already exists
```

**Solutions:**

**Option 1: Use a different ID**

```bash
pwa-forge add https://example.com --id example-2
```

**Option 2: Remove existing PWA first**

```bash
pwa-forge remove example
pwa-forge add https://example.com --id example
```

**Option 3: List existing PWAs to avoid conflicts**

```bash
pwa-forge list
```

### Permission Denied Creating Files

**Problem:** Cannot create files in directories.

```
PermissionError: [Errno 13] Permission denied: '/home/user/.local/share/applications/pwa-forge-app.desktop'
```

**Solution:**

Ensure directories exist and have correct permissions:

```bash
# Create directories
mkdir -p ~/.local/share/applications
mkdir -p ~/.local/share/pwa-forge
mkdir -p ~/.local/bin/pwa-forge-wrappers

# Fix permissions
chmod 755 ~/.local/share/applications
chmod 755 ~/.local/share/pwa-forge
chmod 755 ~/.local/bin
```

## Launch Issues

### PWA Doesn't Appear in Application Menu

**Problem:** PWA was created but doesn't show in launcher.

**Solutions:**

**Option 1: Update desktop database**

```bash
update-desktop-database ~/.local/share/applications
```

**Option 2: Wait a few seconds**

Some desktop environments cache the application list. Wait 10-30 seconds or log out and back in.

**Option 3: Verify desktop file**

```bash
# Check if file exists
ls -la ~/.local/share/applications/pwa-forge-*.desktop

# Verify contents
cat ~/.local/share/applications/pwa-forge-chatgpt.desktop

# Test launching directly
gtk-launch pwa-forge-chatgpt.desktop
```

**Option 4: Audit and fix**

```bash
pwa-forge audit chatgpt --fix
```

### PWA Launches But Shows Error

**Problem:** PWA opens but displays an error page.

**Possible Causes:**

1. **URL changed or site is down**

   Solution: Update the URL
   ```bash
   pwa-forge edit chatgpt
   # Update url field, save
   ```

2. **Browser profile corrupted**

   Solution: Remove and recreate profile
   ```bash
   pwa-forge remove chatgpt --remove-profile
   pwa-forge add https://chat.openai.com --name "ChatGPT"
   ```

3. **Browser flags incompatible**

   Solution: Edit manifest and remove problematic flags
   ```bash
   pwa-forge edit chatgpt
   # Remove or modify flags section
   ```

### PWA Opens in Wrong Browser

**Problem:** PWA uses different browser than specified.

**Solution:**

1. Check manifest:
   ```bash
   pwa-forge list --verbose
   ```

2. Verify browser path:
   ```bash
   pwa-forge config get browsers.chrome
   which google-chrome-stable
   ```

3. Update if needed:
   ```bash
   pwa-forge config set browsers.chrome /usr/bin/google-chrome-stable
   pwa-forge sync chatgpt
   ```

### Wrapper Script Not Executable

**Problem:** Permission denied when launching.

```
bash: /home/user/.local/bin/pwa-forge-wrappers/chatgpt: Permission denied
```

**Solution:**

```bash
# Fix permissions
chmod +x ~/.local/bin/pwa-forge-wrappers/chatgpt

# Or use audit to fix automatically
pwa-forge audit chatgpt --fix
```

## External Link Handling

### Links Open Inside PWA Instead of System Browser

**Problem:** External links don't open in system browser despite configuration.

**Causes & Solutions:**

**1. Userscript not installed**

Solution: Generate and install userscript
```bash
pwa-forge generate-userscript --scheme ff \
  --in-scope-hosts mail.google.com \
  --out ~/.local/share/pwa-forge/userscripts/gmail.user.js

# Install Violentmonkey in PWA, then install the userscript
```

**2. URL handler not registered**

Solution: Install URL handler
```bash
pwa-forge generate-handler --scheme ff --browser firefox
pwa-forge install-handler --scheme ff

# Verify registration
xdg-mime query default x-scheme-handler/ff
```

**3. Wrong in-scope hosts**

Solution: Update userscript with correct hosts
```bash
# Edit the userscript file
# Update IN_SCOPE_HOSTS array
# Reinstall in Violentmonkey
```

**4. Userscript manager not working**

Solution: Try a different extension
- Violentmonkey (recommended)
- Tampermonkey (alternative)
- Greasemonkey (Firefox only)

### URL Handler Not Working

**Problem:** ff:// links don't open in system browser.

**Diagnostic:**

```bash
# Check if handler is registered
xdg-mime query default x-scheme-handler/ff

# Should output: pwa-forge-handler-ff.desktop

# Test handler directly
~/.local/bin/pwa-forge-handler-ff "ff://https%3A%2F%2Fexample.com"
```

**Solutions:**

**If not registered:**

```bash
pwa-forge install-handler --scheme ff
```

**If handler script missing:**

```bash
pwa-forge generate-handler --scheme ff --browser firefox
pwa-forge install-handler --scheme ff
```

**If handler script exists but not working:**

```bash
# Make executable
chmod +x ~/.local/bin/pwa-forge-handler-ff

# Test manually
~/.local/bin/pwa-forge-handler-ff "ff://https%3A%2F%2Fexample.com"
```

## Desktop Integration

### Icon Not Displaying

**Problem:** PWA shows generic icon instead of custom icon.

**Solutions:**

**Option 1: Specify icon explicitly**

```bash
pwa-forge add https://example.com \
  --icon ~/Pictures/example-icon.svg
```

**Option 2: Update existing PWA icon**

```bash
# Edit manifest
pwa-forge edit chatgpt

# Update icon field:
# icon: /home/user/Pictures/chatgpt.svg

# Sync to apply changes
pwa-forge sync chatgpt
```

**Option 3: Use supported format**

Ensure icon is:
- SVG (preferred)
- PNG (256x256 or larger)
- Located in a accessible path

```bash
# Convert if needed
convert icon.png -resize 256x256 icon-resized.png
```

**Option 4: Update icon cache**

```bash
gtk-update-icon-cache ~/.local/share/icons/pwa-forge
```

### Wrong Window Manager Class

**Problem:** Window rules don't work for PWA.

**Diagnostic:**

```bash
# Get WM class of running PWA
xprop WM_CLASS
# Click on PWA window

# Check manifest
pwa-forge list --verbose | grep -A 10 chatgpt
```

**Solution:**

Update WM class:
```bash
pwa-forge edit chatgpt

# Set wm_class to desired value
# wm_class: MyChatGPT

pwa-forge sync chatgpt
```

### PWA Not in Correct Category

**Problem:** PWA appears in wrong application menu category.

**Solution:**

Edit categories:
```bash
pwa-forge edit chatgpt

# Update categories:
# categories:
#   - Network
#   - WebBrowser
#   - Office

pwa-forge sync chatgpt
```

Valid categories: Network, WebBrowser, Utility, Office, Development, AudioVideo, Graphics, Game, Education, Science, System, Settings

## Browser Issues

### Chrome/Chromium Crashes on Launch

**Problem:** Browser crashes immediately when PWA starts.

**Common Causes:**

**1. Wayland/X11 incompatibility**

Solution: Try different platform
```bash
pwa-forge edit chatgpt

# Change ozone_platform from 'wayland' to 'x11' or vice versa
# flags:
#   ozone_platform: x11

pwa-forge sync chatgpt
```

**2. Incompatible flags**

Solution: Remove problematic flags
```bash
pwa-forge edit chatgpt

# Remove or comment out flags causing issues
# Common problematic flags:
# - --disable-gpu
# - --no-sandbox

pwa-forge sync chatgpt
```

**3. Corrupted profile**

Solution: Reset profile
```bash
pwa-forge remove chatgpt --remove-profile
pwa-forge add https://chat.openai.com --name "ChatGPT"
```

### Browser Uses Too Much Memory

**Problem:** High memory usage.

**Solutions:**

**Option 1: Limit cache size**

```bash
pwa-forge edit chatgpt

# Add to chrome_flags:
# --disk-cache-size=104857600  # 100MB

pwa-forge sync chatgpt
```

**Option 2: Use separate profiles**

Each PWA already has isolated profile, but ensure you're not running multiple instances:

```bash
# Check running processes
ps aux | grep pwa-forge

# Use separate profiles for work/personal
pwa-forge add https://app.com --id work-app --profile ~/.config/work/app
pwa-forge add https://app.com --id personal-app --profile ~/.config/personal/app
```

### Browser Version Mismatch

**Problem:** Features not working due to old browser.

**Solution:**

Update browser:
```bash
# Chrome
sudo apt update && sudo apt upgrade google-chrome-stable

# Chromium
sudo apt update && sudo apt upgrade chromium-browser

# Firefox
sudo apt update && sudo apt upgrade firefox
```

## Profile and Data Issues

### Profile Directory Fills Up Disk

**Problem:** Profile directory grows too large.

**Solutions:**

**Option 1: Clear cache**

```bash
# Find profile directory
pwa-forge list --verbose | grep chatgpt -A 5

# Clear cache (PWA must be closed)
rm -rf ~/.config/pwa-forge/apps/chatgpt/Cache
rm -rf ~/.config/pwa-forge/apps/chatgpt/Code\ Cache
```

**Option 2: Limit cache size**

```bash
pwa-forge edit chatgpt

# Add flag:
# --disk-cache-size=104857600  # 100MB

pwa-forge sync chatgpt
```

### Lost Login Sessions

**Problem:** PWA doesn't remember logins.

**Causes:**

1. Profile was deleted
2. Using private/incognito mode
3. Website cookies expired

**Solutions:**

- Ensure profile exists:
  ```bash
  pwa-forge audit chatgpt
  ```

- Don't use `--remove-profile` when recreating PWAs

- Check manifest doesn't have incognito flags

### Cannot Access Old Profile Data

**Problem:** Recreated PWA but lost data.

**Solution:**

If you backed up the profile:
```bash
# Create PWA with same ID
pwa-forge add https://example.com --id old-app

# Stop the PWA
# Restore profile data
cp -r ~/backup/old-app-profile/* ~/.config/pwa-forge/apps/old-app/
```

## Permission Issues

### Cannot Write to ~/.local/bin

**Problem:** Permission denied creating wrapper scripts.

**Solution:**

```bash
# Create directory
mkdir -p ~/.local/bin/pwa-forge-wrappers

# Fix ownership
sudo chown -R $USER:$USER ~/.local/bin

# Fix permissions
chmod -R 755 ~/.local/bin
```

### System-Wide Installation Fails

**Problem:** Trying to install system-wide without sudo.

**Solution:**

Use user mode (default):
```bash
# No sudo needed for user mode
pwa-forge add https://example.com
```

For system-wide (if really needed):
```bash
sudo pwa-forge add https://example.com --system
```

**Note:** System-wide mode is not yet implemented. Use user mode.

## Diagnostic Commands

### Check System Requirements

```bash
pwa-forge doctor
```

This checks:
- Python version
- Browser availability
- XDG utilities
- Directory permissions
- Desktop environment

### Verify PWA Status

```bash
# List all PWAs
pwa-forge list --verbose

# Audit specific PWA
pwa-forge audit chatgpt

# Audit all PWAs
pwa-forge audit

# Fix issues automatically
pwa-forge audit chatgpt --fix
```

### Check Configuration

```bash
# Show all config
pwa-forge config list

# Check specific values
pwa-forge config get default_browser
pwa-forge config get browsers.chrome
pwa-forge config get log_level
```

### View Logs

```bash
# Default log location
tail -f ~/.local/share/pwa-forge/pwa-forge.log

# View with grep
grep ERROR ~/.local/share/pwa-forge/pwa-forge.log

# Last 50 lines
tail -n 50 ~/.local/share/pwa-forge/pwa-forge.log
```

### Test Desktop File

```bash
# Validate desktop file
desktop-file-validate ~/.local/share/applications/pwa-forge-chatgpt.desktop

# Test launching
gtk-launch pwa-forge-chatgpt.desktop

# Or
gio launch ~/.local/share/applications/pwa-forge-chatgpt.desktop
```

### Test Wrapper Script

```bash
# Run wrapper directly
~/.local/bin/pwa-forge-wrappers/chatgpt

# Check if executable
ls -la ~/.local/bin/pwa-forge-wrappers/chatgpt

# View contents
cat ~/.local/bin/pwa-forge-wrappers/chatgpt
```

### Verify XDG Registration

```bash
# Check desktop database
update-desktop-database ~/.local/share/applications

# Query MIME handler
xdg-mime query default x-scheme-handler/ff

# List all handlers
xdg-mime query filetype "ff://test"
```

## Getting Help

If your issue isn't covered here:

1. **Check logs:**
   ```bash
   tail -f ~/.local/share/pwa-forge/pwa-forge.log
   ```

2. **Run diagnostics:**
   ```bash
   pwa-forge doctor
   pwa-forge audit --fix
   ```

3. **Enable debug logging:**
   ```bash
   pwa-forge --verbose --verbose <command>
   # or
   pwa-forge config set log_level debug
   ```

4. **Search existing issues:**
   - GitHub Issues: https://github.com/bigr/pwa_forge/issues

5. **Create a bug report:**
   Include:
   - Output of `pwa-forge doctor`
   - Output of `pwa-forge list --verbose`
   - Relevant log entries
   - Steps to reproduce

## Common Error Messages

### "App not found in registry"

**Cause:** PWA doesn't exist or was removed.

**Solution:**
```bash
# List existing PWAs
pwa-forge list

# Create if needed
pwa-forge add https://example.com --id app-name
```

### "Desktop file not found"

**Cause:** Desktop file was manually deleted or corrupted.

**Solution:**
```bash
pwa-forge sync app-name
```

### "Browser executable not found"

**Cause:** Browser not installed or path incorrect.

**Solution:**
```bash
# Install browser
sudo apt install google-chrome-stable

# Or configure path
pwa-forge config set browsers.chrome /snap/bin/chromium

# Or use different browser
pwa-forge add https://example.com --browser firefox
```

### "Invalid YAML syntax"

**Cause:** Manifest file has syntax errors.

**Solution:**
```bash
# Check manifest
cat ~/.local/share/pwa-forge/apps/app-name/manifest.yaml

# Validate YAML online or with:
python3 -c "import yaml; yaml.safe_load(open('path/to/manifest.yaml'))"

# Restore backup if exists
cp ~/.local/share/pwa-forge/apps/app-name/manifest.yaml.bak \
   ~/.local/share/pwa-forge/apps/app-name/manifest.yaml
```

## See Also

- [USAGE.md](USAGE.md) - Complete usage guide
- [README.md](../README.md) - Quick start
- [TESTING.md](TESTING.md) - Development and testing
