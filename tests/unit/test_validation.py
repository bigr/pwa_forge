"""Unit tests for validation utilities."""

from __future__ import annotations

from pwa_forge.validation import (
    extract_name_from_url,
    generate_id,
    generate_wm_class,
    validate_id,
    validate_url,
)


class TestValidateUrl:
    """Tests for URL validation."""

    def test_valid_http_url(self) -> None:
        """Test validation of valid HTTP URL."""
        is_valid, message = validate_url("http://example.com")
        assert is_valid is True
        assert message == "OK"

    def test_valid_https_url(self) -> None:
        """Test validation of valid HTTPS URL."""
        is_valid, message = validate_url("https://example.com")
        assert is_valid is True
        assert message == "OK"

    def test_valid_url_with_path(self) -> None:
        """Test validation of URL with path."""
        is_valid, message = validate_url("https://example.com/path/to/app")
        assert is_valid is True
        assert message == "OK"

    def test_valid_url_with_query(self) -> None:
        """Test validation of URL with query parameters."""
        is_valid, message = validate_url("https://example.com?param=value")
        assert is_valid is True
        assert message == "OK"

    def test_invalid_scheme_ftp(self) -> None:
        """Test rejection of FTP URLs."""
        is_valid, message = validate_url("ftp://example.com")
        assert is_valid is False
        assert "http" in message.lower()

    def test_invalid_scheme_file(self) -> None:
        """Test rejection of file URLs."""
        is_valid, message = validate_url("file:///path/to/file")
        assert is_valid is False
        assert "http" in message.lower()

    def test_missing_hostname(self) -> None:
        """Test rejection of URL without hostname."""
        is_valid, message = validate_url("https://")
        assert is_valid is False
        assert "hostname" in message.lower()

    def test_localhost_url(self) -> None:
        """Test warning for localhost URLs."""
        is_valid, message = validate_url("http://localhost:8080")
        assert is_valid is True
        assert "localhost" in message.lower()

    def test_localhost_ip(self) -> None:
        """Test warning for 127.0.0.1 URLs."""
        is_valid, message = validate_url("http://127.0.0.1:3000")
        assert is_valid is True
        assert "localhost" in message.lower()

    def test_invalid_url_format(self) -> None:
        """Test rejection of malformed URLs."""
        is_valid, _ = validate_url("not a url")
        assert is_valid is False


class TestGenerateId:
    """Tests for ID generation."""

    def test_simple_name(self) -> None:
        """Test ID generation from simple name."""
        assert generate_id("ChatGPT") == "chatgpt"

    def test_name_with_hyphen(self) -> None:
        """Test ID generation preserves hyphens."""
        assert generate_id("ChatGPT-DNAI") == "chatgpt-dnai"

    def test_name_with_spaces(self) -> None:
        """Test ID generation converts spaces to hyphens."""
        assert generate_id("My App") == "my-app"

    def test_name_with_special_chars(self) -> None:
        """Test ID generation removes special characters."""
        assert generate_id("My App!") == "my-app"
        assert generate_id("App@Home") == "app-home"

    def test_name_with_multiple_spaces(self) -> None:
        """Test ID generation collapses multiple spaces."""
        assert generate_id("App   Name") == "app-name"

    def test_name_with_leading_trailing_spaces(self) -> None:
        """Test ID generation removes leading/trailing hyphens."""
        assert generate_id("  App  ") == "app"

    def test_name_with_underscore(self) -> None:
        """Test ID generation preserves underscores."""
        assert generate_id("my_app") == "my_app"

    def test_long_name(self) -> None:
        """Test ID generation truncates long names."""
        long_name = "a" * 100
        app_id = generate_id(long_name)
        assert len(app_id) <= 64

    def test_empty_name(self) -> None:
        """Test ID generation handles empty string."""
        app_id = generate_id("")
        assert app_id == "app"

    def test_special_chars_only(self) -> None:
        """Test ID generation handles special chars only."""
        app_id = generate_id("!!!")
        assert app_id == "app"

    def test_mixed_case(self) -> None:
        """Test ID generation converts to lowercase."""
        assert generate_id("MyApp") == "myapp"
        assert generate_id("MYAPP") == "myapp"


class TestValidateId:
    """Tests for ID validation."""

    def test_valid_simple_id(self) -> None:
        """Test validation of simple valid ID."""
        is_valid, message = validate_id("myapp")
        assert is_valid is True
        assert message == "OK"

    def test_valid_id_with_hyphen(self) -> None:
        """Test validation of ID with hyphens."""
        is_valid, _ = validate_id("my-app")
        assert is_valid is True

    def test_valid_id_with_underscore(self) -> None:
        """Test validation of ID with underscores."""
        is_valid, _ = validate_id("my_app")
        assert is_valid is True

    def test_valid_id_with_numbers(self) -> None:
        """Test validation of ID with numbers."""
        is_valid, _ = validate_id("app123")
        assert is_valid is True

    def test_valid_id_starting_with_number(self) -> None:
        """Test validation of ID starting with number."""
        is_valid, _ = validate_id("123app")
        assert is_valid is True

    def test_invalid_empty_id(self) -> None:
        """Test rejection of empty ID."""
        is_valid, message = validate_id("")
        assert is_valid is False
        assert "empty" in message.lower()

    def test_invalid_uppercase(self) -> None:
        """Test rejection of ID with uppercase."""
        is_valid, _ = validate_id("MyApp")
        assert is_valid is False

    def test_invalid_spaces(self) -> None:
        """Test rejection of ID with spaces."""
        is_valid, _ = validate_id("my app")
        assert is_valid is False

    def test_invalid_special_chars(self) -> None:
        """Test rejection of ID with special characters."""
        is_valid, _ = validate_id("my@app")
        assert is_valid is False

    def test_invalid_starting_with_hyphen(self) -> None:
        """Test rejection of ID starting with hyphen."""
        is_valid, _ = validate_id("-myapp")
        assert is_valid is False

    def test_invalid_too_long(self) -> None:
        """Test rejection of ID that's too long."""
        long_id = "a" * 65
        is_valid, message = validate_id(long_id)
        assert is_valid is False
        assert "64" in message


class TestGenerateWmClass:
    """Tests for WMClass generation."""

    def test_simple_name(self) -> None:
        """Test WMClass generation from simple name."""
        assert generate_wm_class("chatgpt") == "Chatgpt"

    def test_name_with_hyphen(self) -> None:
        """Test WMClass generation from hyphenated name."""
        assert generate_wm_class("ChatGPT-DNAI") == "ChatgptDnai"

    def test_name_with_spaces(self) -> None:
        """Test WMClass generation from spaced name."""
        assert generate_wm_class("my app") == "MyApp"

    def test_mixed_case_preserved(self) -> None:
        """Test WMClass generation capitalizes words."""
        assert generate_wm_class("myApp") == "Myapp"

    def test_multiple_words(self) -> None:
        """Test WMClass generation from multiple words."""
        assert generate_wm_class("Google Chrome App") == "GoogleChromeApp"

    def test_special_chars_removed(self) -> None:
        """Test WMClass generation removes special characters."""
        assert generate_wm_class("My@App!") == "MyApp"

    def test_empty_name(self) -> None:
        """Test WMClass generation handles empty string."""
        wm_class = generate_wm_class("")
        assert wm_class == "App"

    def test_special_chars_only(self) -> None:
        """Test WMClass generation handles special chars only."""
        wm_class = generate_wm_class("!!!")
        assert wm_class == "App"

    def test_uppercase_words(self) -> None:
        """Test WMClass generation with all caps."""
        assert generate_wm_class("GMAIL") == "Gmail"


class TestExtractNameFromUrl:
    """Tests for name extraction from URL."""

    def test_simple_domain(self) -> None:
        """Test name extraction from simple domain."""
        assert extract_name_from_url("https://example.com") == "Example"

    def test_subdomain(self) -> None:
        """Test name extraction from subdomain."""
        assert extract_name_from_url("https://chat.openai.com") == "Chat"

    def test_www_prefix(self) -> None:
        """Test name extraction removes www prefix."""
        assert extract_name_from_url("https://www.example.com") == "Example"

    def test_with_path(self) -> None:
        """Test name extraction ignores path."""
        assert extract_name_from_url("https://mail.google.com/mail/u/0") == "Mail"

    def test_with_port(self) -> None:
        """Test name extraction handles port."""
        assert extract_name_from_url("https://localhost:8080") == "Localhost"

    def test_complex_subdomain(self) -> None:
        """Test name extraction from complex subdomain."""
        assert extract_name_from_url("https://app.example.com") == "App"

    def test_ip_address(self) -> None:
        """Test name extraction from IP address."""
        name = extract_name_from_url("https://192.168.1.1")
        assert name  # Should return something, even if just "App"

    def test_invalid_url(self) -> None:
        """Test name extraction handles invalid URL."""
        name = extract_name_from_url("not a url")
        assert name == "Not"  # Extracts first word

    def test_invalid_url_no_words(self) -> None:
        """Test name extraction with no extractable words."""
        name = extract_name_from_url("://")
        assert name == "App"  # Fallback
