"""Test userscript window.open() patching functionality."""

import urllib.parse

import pytest

try:
    from playwright.sync_api import Page, expect

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = None
    expect = None

pytestmark = pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")


def test_window_open_external_url_rewritten(test_page: Page, captured_navigation_urls: list[str]) -> None:
    """Verify window.open() with external URL uses custom scheme."""
    # Click button that calls window.open with external URL
    open_button = test_page.locator("#window-open-btn")
    expect(open_button).to_be_visible()

    open_button.click()

    # Wait for navigation attempt
    test_page.wait_for_timeout(200)

    # Verify a testff: URL was captured
    testff_urls = [url for url in captured_navigation_urls if url.startswith("testff:")]
    assert len(testff_urls) > 0, "Expected window.open to trigger testff: navigation"

    # Verify the URL is correct
    decoded_url = urllib.parse.unquote(testff_urls[0].replace("testff:", ""))
    assert "external-site.com/popup" in decoded_url


def test_window_open_internal_url_not_rewritten(test_page: Page, captured_navigation_urls: list[str]) -> None:
    """Verify window.open() with internal (in-scope) URL is NOT rewritten."""
    # Click button that calls window.open with internal URL
    open_button = test_page.locator("#window-open-internal-btn")
    expect(open_button).to_be_visible()

    # Clear any previous captures
    captured_navigation_urls.clear()

    open_button.click()

    # Wait for navigation attempt
    test_page.wait_for_timeout(200)

    # Verify NO testff: URL was captured for internal URL
    testff_urls = [url for url in captured_navigation_urls if url.startswith("testff:")]
    assert len(testff_urls) == 0, "Internal URL should not be rewritten to testff: scheme"

    # Verify the original URL was used
    example_urls = [url for url in captured_navigation_urls if "example.com/internal-popup" in url]
    assert len(example_urls) > 0, "Expected original internal URL to be used"
