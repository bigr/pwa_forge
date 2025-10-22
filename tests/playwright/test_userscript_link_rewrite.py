"""Test userscript external link rewriting functionality."""

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


def test_external_link_rewritten(test_page: Page, captured_navigation_urls: list[str]) -> None:
    """Verify external links are rewritten to custom scheme."""
    # Click external link
    external_link = test_page.locator("#external-link")
    expect(external_link).to_be_visible()

    # Verify the href attribute was rewritten
    href = external_link.get_attribute("href")
    assert href is not None
    assert href.startswith("testff:"), f"Expected link to be rewritten to testff: scheme, got: {href}"

    # Verify the URL is properly encoded
    encoded_url = href.replace("testff:", "")
    decoded_url = urllib.parse.unquote(encoded_url)
    assert decoded_url == "https://external-site.com/page"

    # Verify target and rel attributes were set
    assert external_link.get_attribute("target") == "_blank"
    assert "noopener" in (external_link.get_attribute("rel") or "")


def test_internal_link_not_rewritten(test_page: Page) -> None:
    """Verify internal (in-scope) links are NOT rewritten."""
    internal_link = test_page.locator("#internal-link")
    expect(internal_link).to_be_visible()

    href = internal_link.get_attribute("href")
    assert href is not None
    assert not href.startswith("testff:"), f"Internal link should not be rewritten, got: {href}"
    assert href == "/internal"


def test_same_site_link_not_rewritten(test_page: Page) -> None:
    """Verify same-site (in-scope) links are NOT rewritten."""
    same_site_link = test_page.locator("#same-site-link")
    expect(same_site_link).to_be_visible()

    href = same_site_link.get_attribute("href")
    assert href is not None
    assert not href.startswith("testff:"), f"Same-site link should not be rewritten, got: {href}"
    assert "same-site.com" in href


def test_mailto_link_not_rewritten(test_page: Page) -> None:
    """Verify mailto: links are NOT rewritten."""
    mailto_link = test_page.locator("#mailto-link")
    expect(mailto_link).to_be_visible()

    href = mailto_link.get_attribute("href")
    assert href is not None
    assert href.startswith("mailto:"), f"Mailto link should not be rewritten, got: {href}"


def test_tel_link_not_rewritten(test_page: Page) -> None:
    """Verify tel: links are NOT rewritten."""
    tel_link = test_page.locator("#tel-link")
    expect(tel_link).to_be_visible()

    href = tel_link.get_attribute("href")
    assert href is not None
    assert href.startswith("tel:"), f"Tel link should not be rewritten, got: {href}"


def test_click_external_link_triggers_navigation(test_page: Page, captured_navigation_urls: list[str]) -> None:
    """Verify clicking external link triggers navigation to custom scheme URL."""
    external_link = test_page.locator("#external-link")
    expect(external_link).to_be_visible()

    # Click the link
    external_link.click()

    # Wait a moment for navigation to be captured
    test_page.wait_for_timeout(100)

    # Verify a testff: URL was captured
    testff_urls = [url for url in captured_navigation_urls if url.startswith("testff:")]
    assert len(testff_urls) > 0, "Expected at least one testff: navigation"

    # Verify the URL is correct
    decoded_url = urllib.parse.unquote(testff_urls[0].replace("testff:", ""))
    assert "external-site.com" in decoded_url


def test_dynamic_link_rewritten(test_page: Page) -> None:
    """Verify dynamically added links are rewritten via MutationObserver."""
    # Initially no dynamic link
    dynamic_link = test_page.locator("#dynamic-external-link")
    expect(dynamic_link).not_to_be_visible()

    # Add dynamic link
    add_button = test_page.locator("#add-dynamic-link")
    add_button.click()

    # Wait for link to appear and be processed
    expect(dynamic_link).to_be_visible()
    test_page.wait_for_timeout(100)

    # Verify it was rewritten
    href = dynamic_link.get_attribute("href")
    assert href is not None
    assert href.startswith("testff:"), f"Dynamic link should be rewritten, got: {href}"

    # Verify the encoded URL
    encoded_url = href.replace("testff:", "")
    decoded_url = urllib.parse.unquote(encoded_url)
    assert decoded_url == "https://dynamic-external.com/page"
