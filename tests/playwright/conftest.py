"""Fixtures and configuration for Playwright browser integration tests."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

try:
    from playwright.sync_api import Browser, BrowserContext, Page

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # Define type aliases for type checking when playwright is not installed
    Browser = Any
    BrowserContext = Any
    Page = Any

from pwa_forge.templates import TemplateEngine

# Skip all tests in this directory if Playwright is not available
pytestmark = pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically mark all tests in this directory as playwright tests."""
    for item in items:
        if "playwright" in str(item.fspath):
            item.add_marker(pytest.mark.playwright)


@pytest.fixture(scope="session")
def template_renderer() -> TemplateEngine:
    """Provide template renderer for generating test userscripts."""
    return TemplateEngine()


@pytest.fixture
def temp_test_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test artifacts."""
    temp_dir = Path(tempfile.mkdtemp(prefix="pwa_forge_test_"))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_userscript(template_renderer: TemplateEngine, temp_test_dir: Path) -> Path:
    """Generate a test userscript with custom scheme handler."""
    userscript_content = template_renderer.render_userscript(
        url_pattern="*://*/*",
        in_scope_hosts=["example.com", "same-site.com"],
        scheme="testff",
    )

    userscript_path = temp_test_dir / "test-userscript.js"
    userscript_path.write_text(userscript_content)
    return userscript_path


@pytest.fixture
def test_html_page(temp_test_dir: Path) -> Path:
    """Create a test HTML page with various link types."""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PWA Forge Test Page</title>
</head>
<body>
    <h1>Link Handler Test Page</h1>

    <!-- Internal link (same domain) -->
    <a id="internal-link" href="/internal">Internal Link</a>

    <!-- External link (different domain) -->
    <a id="external-link" href="https://external-site.com/page">External Link</a>

    <!-- Same-site link (should be in-scope) -->
    <a id="same-site-link" href="https://same-site.com/page">Same Site Link</a>

    <!-- Mailto link (should not be rewritten) -->
    <a id="mailto-link" href="mailto:test@example.com">Email Link</a>

    <!-- Tel link (should not be rewritten) -->
    <a id="tel-link" href="tel:+1234567890">Phone Link</a>

    <!-- Button for testing window.open -->
    <button id="window-open-btn">Open External Window</button>

    <!-- Button for testing window.open with internal URL -->
    <button id="window-open-internal-btn">Open Internal Window</button>

    <!-- Container for dynamically added links -->
    <div id="dynamic-container"></div>

    <!-- Button to add dynamic link -->
    <button id="add-dynamic-link">Add Dynamic Link</button>

    <script>
        document.getElementById('window-open-btn').addEventListener('click', () => {
            window.open('https://external-site.com/popup', '_blank');
        });

        document.getElementById('window-open-internal-btn').addEventListener('click', () => {
            window.open('https://example.com/internal-popup', '_blank');
        });

        document.getElementById('add-dynamic-link').addEventListener('click', () => {
            const container = document.getElementById('dynamic-container');
            const link = document.createElement('a');
            link.id = 'dynamic-external-link';
            link.href = 'https://dynamic-external.com/page';
            link.textContent = 'Dynamic External Link';
            container.appendChild(link);
        });
    </script>
</body>
</html>"""

    html_path = temp_test_dir / "test-page.html"
    html_path.write_text(html_content)
    return html_path


@pytest.fixture
def browser_context_with_userscript(browser: Browser, test_userscript: Path) -> Generator[BrowserContext, None, None]:
    """Create a browser context with userscript injected."""
    context = browser.new_context()

    # Inject userscript into all pages
    userscript_content = test_userscript.read_text()
    context.add_init_script(userscript_content)

    yield context
    context.close()


@pytest.fixture
def test_page(browser_context_with_userscript: BrowserContext, test_html_page: Path) -> Generator[Page, None, None]:
    """Create a page with userscript loaded and navigate to test page."""
    page = browser_context_with_userscript.new_page()

    # Set up console message collection
    console_messages: list[dict[str, Any]] = []
    page.on("console", lambda msg: console_messages.append({"type": msg.type, "text": msg.text}))

    # Navigate to test page
    page.goto(f"file://{test_html_page}")

    # Attach console messages to page for later inspection
    page._console_messages = console_messages

    yield page
    page.close()


@pytest.fixture
def captured_navigation_urls(test_page: Page) -> list[str]:
    """Capture URLs from navigation attempts (including custom schemes)."""
    captured_urls: list[str] = []

    def handle_navigation(route: Any, request: Any) -> None:
        """Capture navigation URL and abort to prevent actual navigation."""
        url = request.url
        captured_urls.append(url)
        # Abort custom scheme navigations (they won't resolve)
        if url.startswith("testff:"):
            route.abort()
        else:
            route.continue_()

    # Intercept all navigation
    test_page.route("**/*", handle_navigation)

    return captured_urls
