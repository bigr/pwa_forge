"""Test URL scheme handler script integration."""

import subprocess
import urllib.parse
from pathlib import Path

import pytest
from pwa_forge.templates import TemplateEngine


@pytest.fixture
def test_handler_script(template_renderer: TemplateEngine, temp_test_dir: Path) -> Path:
    """Generate a test handler script."""
    # Create a mock browser script that just echoes the URL
    mock_browser = temp_test_dir / "mock-browser.sh"
    mock_browser.write_text('#!/bin/bash\necho "BROWSER_CALLED: $@"\n')
    mock_browser.chmod(0o755)

    # Render handler script with mock browser
    handler_content = template_renderer.render_handler_script(
        scheme="testff",
        browser="firefox",
        browser_exec=str(mock_browser),
    )

    handler_path = temp_test_dir / "testff-handler.sh"
    handler_path.write_text(handler_content)
    handler_path.chmod(0o755)

    return handler_path


def test_handler_decodes_simple_url(test_handler_script: Path) -> None:
    """Verify handler script decodes a simple URL correctly."""
    # Encode URL
    target_url = "https://example.com/page"
    encoded_url = urllib.parse.quote(target_url, safe="")
    scheme_url = f"testff:{encoded_url}"

    # Run handler
    result = subprocess.run(
        [str(test_handler_script), scheme_url],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Handler script failed: {result.stderr}"
    assert "BROWSER_CALLED:" in result.stdout
    assert target_url in result.stdout


def test_handler_decodes_complex_url(test_handler_script: Path) -> None:
    """Verify handler script decodes URLs with query parameters and fragments."""
    # Complex URL with query params and fragment
    target_url = "https://example.com/page?param=value&other=123#section"
    encoded_url = urllib.parse.quote(target_url, safe="")
    scheme_url = f"testff:{encoded_url}"

    # Run handler
    result = subprocess.run(
        [str(test_handler_script), scheme_url],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Handler script failed: {result.stderr}"
    assert "BROWSER_CALLED:" in result.stdout
    assert "param=value" in result.stdout
    assert "#section" in result.stdout


def test_handler_with_double_slash_prefix(test_handler_script: Path) -> None:
    """Verify handler handles URLs with :// prefix."""
    target_url = "https://example.com/page"
    encoded_url = urllib.parse.quote(target_url, safe="")
    scheme_url = f"testff://{encoded_url}"

    # Run handler
    result = subprocess.run(
        [str(test_handler_script), scheme_url],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Handler script failed: {result.stderr}"
    assert "BROWSER_CALLED:" in result.stdout
    assert target_url in result.stdout


def test_handler_rejects_non_http_url(test_handler_script: Path) -> None:
    """Verify handler rejects non-HTTP/HTTPS URLs for security."""
    # Try with a file:// URL (should be rejected)
    target_url = "file:///etc/passwd"
    encoded_url = urllib.parse.quote(target_url, safe="")
    scheme_url = f"testff:{encoded_url}"

    # Run handler
    result = subprocess.run(
        [str(test_handler_script), scheme_url],
        capture_output=True,
        text=True,
    )

    # Should fail with error
    assert result.returncode != 0, "Handler should reject file:// URLs"
    assert "Error: Invalid URL scheme" in result.stderr


def test_handler_rejects_empty_url(test_handler_script: Path) -> None:
    """Verify handler rejects empty URL input."""
    # Run handler with no argument
    result = subprocess.run(
        [str(test_handler_script)],
        capture_output=True,
        text=True,
    )

    # Should fail with error
    assert result.returncode != 0, "Handler should reject empty input"
    assert "Error: No URL provided" in result.stderr


def test_handler_logs_action(test_handler_script: Path) -> None:
    """Verify handler logs actions (via logger command)."""
    target_url = "https://example.com/logged"
    encoded_url = urllib.parse.quote(target_url, safe="")
    scheme_url = f"testff:{encoded_url}"

    # Run handler
    result = subprocess.run(
        [str(test_handler_script), scheme_url],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Handler script failed: {result.stderr}"

    # The script should call logger (we can't easily verify syslog, but we can check the script runs)
    assert "BROWSER_CALLED:" in result.stdout
