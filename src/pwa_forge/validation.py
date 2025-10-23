"""Validation and generation utilities for PWA Forge."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class ValidationStatus:
    """URL validation result status codes."""

    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


def validate_url(url: str, verify: bool = False, timeout: int = 5) -> tuple[bool, str, str]:
    """Validate URL format and optionally check accessibility.

    Args:
        url: URL to validate.
        verify: If True, attempt to connect to the URL.
        timeout: Connection timeout in seconds for verification.

    Returns:
        Tuple of (is_valid, status, message) where:
        - is_valid: True if URL is valid (may have warnings)
        - status: One of ValidationStatus.OK, ValidationStatus.WARNING, ValidationStatus.ERROR
        - message: Description of the validation result
    """
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        logger.debug(f"URL parsing failed for '{url}': {e}")
        return False, ValidationStatus.ERROR, f"Invalid URL format: {e}"

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        logger.debug(f"Invalid URL scheme: {parsed.scheme}")
        return False, ValidationStatus.ERROR, "URL must use http:// or https://"

    # Check host
    if not parsed.netloc:
        logger.debug("URL missing hostname")
        return False, ValidationStatus.ERROR, "URL must include a hostname"

    # Warn about localhost
    hostname = parsed.netloc.split(":")[0] if ":" in parsed.netloc else parsed.netloc
    if hostname in ("localhost", "127.0.0.1", "::1"):
        logger.warning(f"Localhost URL detected: {url}")
        return True, ValidationStatus.WARNING, "localhost URLs won't work from system launcher"

    # Optional connectivity check
    if verify:
        try:
            logger.debug(f"Verifying URL accessibility: {url}")
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code >= 400:
                logger.warning(f"URL returned HTTP {response.status_code}: {url}")
                return False, ValidationStatus.ERROR, f"URL returned HTTP {response.status_code}"
        except requests.RequestException as e:
            logger.warning(f"URL not accessible: {url} - {e}")
            return False, ValidationStatus.ERROR, f"URL not accessible: {e}"

    logger.debug(f"URL validation passed: {url}")
    return True, ValidationStatus.OK, "OK"


def generate_id(name: str) -> str:
    """Generate a valid app ID from a display name.

    Valid ID format:
    - Lowercase only
    - Alphanumeric plus '-' and '_'
    - No spaces or special characters
    - Maximum 64 characters
    - Must start with letter or digit

    Args:
        name: Display name to generate ID from.

    Returns:
        Generated ID string.

    Examples:
        >>> generate_id("ChatGPT-DNAI")
        'chatgpt-dnai'
        >>> generate_id("My App!")
        'my-app'
        >>> generate_id("App   Name")
        'app-name'
    """
    # Convert to lowercase
    id_str = name.lower()

    # Replace spaces and special chars with hyphen
    id_str = re.sub(r"[^a-z0-9_-]+", "-", id_str)

    # Remove leading/trailing hyphens
    id_str = id_str.strip("-")

    # Collapse multiple hyphens
    id_str = re.sub(r"-+", "-", id_str)

    # Truncate if too long
    id_str = id_str[:64]

    # Ensure it starts with alphanumeric
    if id_str and not id_str[0].isalnum():
        id_str = "app-" + id_str

    # Fallback for empty string
    if not id_str:
        id_str = "app"

    logger.debug(f"Generated ID '{id_str}' from name '{name}'")
    return id_str


def validate_id(app_id: str) -> tuple[bool, str]:
    """Validate an app ID format.

    Args:
        app_id: App ID to validate.

    Returns:
        Tuple of (is_valid, message).
    """
    # Check length
    if len(app_id) == 0:
        return False, "ID cannot be empty"
    if len(app_id) > 64:
        return False, "ID must be 64 characters or less"

    # Check format
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", app_id):
        return (
            False,
            "ID must start with a letter or digit and contain only lowercase letters, digits, hyphens, and underscores",
        )

    logger.debug(f"ID validation passed: {app_id}")
    return True, "OK"


def generate_wm_class(app_name: str) -> str:
    """Generate StartupWMClass from app name.

    Rules:
    - CamelCase format
    - Only alphanumeric characters
    - Each word capitalized

    Args:
        app_name: Application display name.

    Returns:
        Generated WMClass string.

    Examples:
        >>> generate_wm_class("ChatGPT-DNAI")
        'ChatgptDnai'
        >>> generate_wm_class("my app")
        'MyApp'
        >>> generate_wm_class("GMail")
        'Gmail'
    """
    # Extract words (alphanumeric sequences)
    words = re.findall(r"\w+", app_name)

    # Capitalize each word
    wm_class = "".join(word.capitalize() for word in words)

    # Fallback for empty string
    if not wm_class:
        wm_class = "App"

    logger.debug(f"Generated WMClass '{wm_class}' from name '{app_name}'")
    return wm_class


def extract_name_from_url(url: str) -> str:
    """Extract a reasonable app name from a URL.

    Args:
        url: URL to extract name from.

    Returns:
        Extracted name or domain.

    Examples:
        >>> extract_name_from_url("https://chat.openai.com")
        'Chat'
        >>> extract_name_from_url("https://example.com")
        'Example'
        >>> extract_name_from_url("https://mail.google.com")
        'Mail'
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc

        # If no netloc, it's not a valid URL
        if not hostname:
            raise ValueError("No hostname found in URL")

        # Remove port if present
        if ":" in hostname:
            hostname = hostname.split(":")[0]

        # Remove www. prefix
        if hostname.startswith("www."):
            hostname = hostname[4:]

        # Try to get the subdomain or first part
        parts = hostname.split(".")
        if len(parts) > 2:
            # Use subdomain (e.g., "chat" from "chat.openai.com")
            name = parts[0]
        elif len(parts) == 2:
            # Use domain name (e.g., "example" from "example.com")
            name = parts[0]
        else:
            # Fallback to full hostname
            name = hostname

        # Capitalize first letter
        name = name.capitalize()

        logger.debug(f"Extracted name '{name}' from URL '{url}'")
        return name

    except Exception as e:
        logger.warning(f"Failed to extract name from URL '{url}': {e}")
        # Try to return something from the invalid input
        if url:
            # Take first word-like sequence
            words: list[str] = re.findall(r"\w+", url)
            if words:
                return words[0].capitalize()
        return "App"
