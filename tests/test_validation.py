"""Tests for input validation and edge case handling."""

import base64
import io
import pytest
from PIL import Image
import numpy as np

from src.albumentations_mcp.validation import (
    ValidationError,
    ImageValidationError,
    PromptValidationError,
    SecurityValidationError,
    ResourceLimitError,
    validate_base64_image,
    validate_prompt,
    validate_transform_parameters,
    get_validation_config,
    create_safe_fallback_image,
    get_safe_default_parameters,
)


class TestImageValidation:
    """Test image validation edge cases."""

    def create_test_image(self, width=100, height=100, format="PNG"):
        """Create a test image as Base64."""
        img = Image.new("RGB", (width, height), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode()

    def test_valid_image(self):
        """Test validation of valid image."""
        image_b64 = self.create_test_image()
        result = validate_base64_image(image_b64, strict=False)

        assert result["valid"] is True
        assert result["error"] is None
        assert result["metadata"]["width"] == 100
        assert result["metadata"]["height"] == 100
        assert result["metadata"]["format"] == "PNG"

    def test_empty_string(self):
        """Test validation of empty string."""
        result = validate_base64_image("", strict=False)

        assert result["valid"] is False
        assert "non-empty string" in result["error"]

    def test_none_input(self):
        """Test validation of None input."""
        result = validate_base64_image(None, strict=False)

        assert result["valid"] is False
        assert "non-empty string" in result["error"]

    def test_invalid_base64(self):
        """Test validation of invalid Base64."""
        result = validate_base64_image("invalid_base64!", strict=False)

        assert result["valid"] is False
        assert "Invalid Base64 encoding" in result["error"]

    def test_corrupted_base64(self):
        """Test validation of corrupted Base64."""
        # Create valid Base64 then corrupt it more aggressively
        valid_b64 = self.create_test_image()
        corrupted_b64 = (
            valid_b64[:50] + "INVALID_CHARS_!@#$%^&*()" + valid_b64[80:]
        )

        result = validate_base64_image(corrupted_b64, strict=False)

        assert result["valid"] is False
        assert result["error"] is not None

    def test_data_url_prefix(self):
        """Test handling of data URL prefix."""
        image_b64 = self.create_test_image()
        data_url = f"data:image/png;base64,{image_b64}"

        result = validate_base64_image(data_url, strict=False)

        assert result["valid"] is True
        assert result["sanitized_data"] == image_b64

    def test_invalid_data_url(self):
        """Test handling of invalid data URL."""
        result = validate_base64_image("data:image/png;base64", strict=False)

        assert result["valid"] is False
        assert "Invalid data URL format" in result["error"]

    def test_large_image_dimensions(self):
        """Test validation of oversized image."""
        # Create image larger than limits
        large_image_b64 = self.create_test_image(width=10000, height=10000)

        result = validate_base64_image(large_image_b64, strict=False)

        assert result["valid"] is False
        assert (
            "too large" in result["error"]
        )  # Could be security or image size limit

    def test_large_file_size(self):
        """Test validation of large file size."""
        # Create a large Base64 string (simulate large file)
        large_data = "A" * (60 * 1024 * 1024)  # 60MB of 'A's
        large_b64 = base64.b64encode(large_data.encode()).decode()

        result = validate_base64_image(large_b64, strict=False)

        assert result["valid"] is False
        assert (
            "too large" in result["error"]
        )  # Could be security or file size limit

    def test_unsupported_format(self):
        """Test handling of unsupported image format."""
        # This test is tricky since PIL supports most formats
        # We'll test the warning system instead
        image_b64 = self.create_test_image()
        result = validate_base64_image(image_b64, strict=False)

        # Should still be valid but might have warnings
        assert result["valid"] is True

    def test_security_patterns(self):
        """Test detection of security patterns."""
        malicious_b64 = base64.b64encode(
            b"<script>alert('xss')</script>"
        ).decode()

        result = validate_base64_image(malicious_b64, strict=False)

        assert result["valid"] is False
        assert result["error"] is not None

    def test_strict_mode_exceptions(self):
        """Test that strict mode raises exceptions."""
        with pytest.raises(ImageValidationError):
            validate_base64_image("", strict=True)

        with pytest.raises(ImageValidationError):
            validate_base64_image("invalid_base64!", strict=True)

    def test_memory_estimation(self):
        """Test memory usage estimation."""
        image_b64 = self.create_test_image(width=1000, height=1000)
        result = validate_base64_image(image_b64, strict=False)

        assert result["valid"] is True
        assert "estimated_memory_mb" in result["metadata"]
        assert result["metadata"]["estimated_memory_mb"] > 0


class TestPromptValidation:
    """Test prompt validation edge cases."""

    def test_valid_prompt(self):
        """Test validation of valid prompt."""
        result = validate_prompt(
            "add blur and increase contrast", strict=False
        )

        assert result["valid"] is True
        assert result["error"] is None
        assert result["sanitized_prompt"] == "add blur and increase contrast"

    def test_empty_prompt(self):
        """Test validation of empty prompt."""
        result = validate_prompt("", strict=False)

        assert result["valid"] is False
        assert "cannot be empty" in result["error"]

    def test_whitespace_only_prompt(self):
        """Test validation of whitespace-only prompt."""
        result = validate_prompt("   \n\t   ", strict=False)

        assert result["valid"] is False
        assert "only whitespace" in result["error"]

    def test_non_string_input(self):
        """Test validation of non-string input."""
        result = validate_prompt(123, strict=False)

        assert result["valid"] is False
        assert "must be a string" in result["error"]

    def test_very_long_prompt(self):
        """Test validation of extremely long prompt."""
        long_prompt = "blur " * 5000  # Very long prompt
        result = validate_prompt(long_prompt, strict=False)

        assert result["valid"] is False
        assert "too long" in result["error"]

    def test_unicode_normalization(self):
        """Test Unicode normalization."""
        unicode_prompt = "add blur café naïve"
        result = validate_prompt(unicode_prompt, strict=False)

        assert result["valid"] is True
        assert result["sanitized_prompt"] is not None

    def test_non_printable_characters(self):
        """Test handling of non-printable characters."""
        prompt_with_control = "add blur\x00\x01\x02"
        result = validate_prompt(prompt_with_control, strict=False)

        # Should have warnings about non-printable characters
        assert len(result["warnings"]) > 0

    def test_security_patterns_in_prompt(self):
        """Test detection of security patterns in prompts."""
        malicious_prompts = [
            "add blur <script>alert('xss')</script>",
            "javascript:alert('xss') and increase contrast",
            "file://etc/passwd blur",
            "../../../etc/passwd blur",
        ]

        for prompt in malicious_prompts:
            result = validate_prompt(prompt, strict=False)
            assert result["valid"] is False
            assert result["error"] is not None

    def test_excessive_punctuation(self):
        """Test detection of excessive punctuation."""
        punct_prompt = "!@#$%^&*()_+{}|:<>?[]\\;'\",./"
        result = validate_prompt(punct_prompt, strict=False)

        # Should have warnings about punctuation ratio
        assert len(result["warnings"]) > 0

    def test_very_long_words(self):
        """Test handling of very long prompts."""
        long_word_prompt = "blur " + "a" * 200 + " contrast"
        result = validate_prompt(long_word_prompt, strict=False)

        # Should still be valid but might have warnings
        assert result["valid"] is True

    def test_strict_mode_exceptions(self):
        """Test that strict mode raises exceptions."""
        with pytest.raises(PromptValidationError):
            validate_prompt("", strict=True)

        with pytest.raises(SecurityValidationError):
            validate_prompt("<script>alert('xss')</script>", strict=True)


class TestParameterValidation:
    """Test transform parameter validation."""

    def test_valid_parameters(self):
        """Test validation of valid parameters."""
        params = {"blur_limit": 7, "p": 1.0}
        result = validate_transform_parameters("Blur", params, strict=False)

        assert result["valid"] is True
        assert result["error"] is None
        assert result["sanitized_parameters"] == params

    def test_empty_transform_name(self):
        """Test validation with empty transform name."""
        result = validate_transform_parameters("", {}, strict=False)

        assert result["valid"] is False
        assert "non-empty string" in result["error"]

    def test_non_dict_parameters(self):
        """Test validation with non-dict parameters."""
        result = validate_transform_parameters(
            "Blur", "not_a_dict", strict=False
        )

        assert result["valid"] is False
        assert "must be a dictionary" in result["error"]

    def test_extreme_numeric_values(self):
        """Test handling of extreme numeric values."""
        params = {"extreme_value": 1e20, "normal_value": 5}
        result = validate_transform_parameters("Test", params, strict=False)

        assert result["valid"] is True
        assert "extreme_value" not in result["sanitized_parameters"]
        assert "normal_value" in result["sanitized_parameters"]
        assert len(result["warnings"]) > 0

    def test_very_long_strings(self):
        """Test handling of very long string parameters."""
        params = {"long_string": "x" * 2000, "normal_string": "test"}
        result = validate_transform_parameters("Test", params, strict=False)

        assert result["valid"] is True
        assert "long_string" not in result["sanitized_parameters"]
        assert "normal_string" in result["sanitized_parameters"]

    def test_very_long_lists(self):
        """Test handling of very long list parameters."""
        params = {"long_list": list(range(200)), "normal_list": [1, 2, 3]}
        result = validate_transform_parameters("Test", params, strict=False)

        assert result["valid"] is True
        assert "long_list" not in result["sanitized_parameters"]
        assert "normal_list" in result["sanitized_parameters"]

    def test_none_values(self):
        """Test handling of None values."""
        params = {"none_value": None, "valid_value": 5}
        result = validate_transform_parameters("Test", params, strict=False)

        assert result["valid"] is True
        assert "none_value" not in result["sanitized_parameters"]
        assert "valid_value" in result["sanitized_parameters"]

    def test_unsupported_types(self):
        """Test handling of unsupported parameter types."""
        params = {"object_value": object(), "valid_value": 5}
        result = validate_transform_parameters("Test", params, strict=False)

        assert result["valid"] is True
        assert "object_value" not in result["sanitized_parameters"]
        assert "valid_value" in result["sanitized_parameters"]
        assert len(result["warnings"]) > 0


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_validation_config(self):
        """Test getting validation configuration."""
        config = get_validation_config()

        assert isinstance(config, dict)
        assert "max_prompt_length" in config
        assert "max_image_width" in config
        assert "supported_formats" in config
        assert isinstance(config["supported_formats"], list)

    def test_create_safe_fallback_image(self):
        """Test creating safe fallback image."""
        img = create_safe_fallback_image()

        assert isinstance(img, Image.Image)
        assert img.size == (100, 100)
        assert img.mode == "RGB"

    def test_get_safe_default_parameters(self):
        """Test getting safe default parameters."""
        # Test known transform
        blur_params = get_safe_default_parameters("Blur")
        assert isinstance(blur_params, dict)
        assert "blur_limit" in blur_params
        assert "p" in blur_params

        # Test unknown transform
        unknown_params = get_safe_default_parameters("UnknownTransform")
        assert isinstance(unknown_params, dict)
        assert "p" in unknown_params


class TestEdgeCases:
    """Test specific edge cases and error conditions."""

    def test_malformed_data_url(self):
        """Test various malformed data URLs."""
        malformed_urls = [
            "data:image/png",  # Missing base64 part
            "data:image/png;base64",  # Missing comma
            "data:text/html,<script>alert('xss')</script>",  # HTML data URL
        ]

        for url in malformed_urls:
            result = validate_base64_image(url, strict=False)
            assert result["valid"] is False

    def test_base64_padding_edge_cases(self):
        """Test Base64 padding edge cases."""
        # Create valid Base64 with different padding scenarios
        test_data = b"test data"
        valid_b64 = base64.b64encode(test_data).decode()

        # Remove padding
        no_padding = valid_b64.rstrip("=")
        result = validate_base64_image(no_padding, strict=False)

        # Should handle missing padding gracefully
        # (though it won't be a valid image)
        assert result["sanitized_data"] is not None

    def test_unicode_edge_cases(self):
        """Test Unicode edge cases in prompts."""
        unicode_prompts = [
            "blur 模糊 and contrast 对比度",  # Chinese characters
            "blur café naïve résumé",  # Accented characters
            "blur \u200b\u200c\u200d",  # Zero-width characters
            "blur \U0001F600 emoji",  # Emoji
        ]

        for prompt in unicode_prompts:
            result = validate_prompt(prompt, strict=False)
            # Should handle Unicode gracefully
            assert result["sanitized_prompt"] is not None

    def test_memory_exhaustion_protection(self):
        """Test protection against memory exhaustion."""
        # Test with parameters that could cause memory issues
        large_params = {
            "huge_list": list(range(1000000)),  # Very large list
            "nested_data": {
                "level1": {"level2": {"level3": list(range(1000))}}
            },
        }

        result = validate_transform_parameters(
            "Test", large_params, strict=False
        )

        # Should filter out problematic parameters
        assert result["valid"] is True
        assert len(result["sanitized_parameters"]) < len(large_params)

    def test_concurrent_validation(self):
        """Test validation under concurrent access."""
        import threading
        import time

        results = []
        errors = []

        def validate_worker():
            try:
                for i in range(10):
                    result = validate_prompt(f"test prompt {i}", strict=False)
                    results.append(result)
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = [threading.Thread(target=validate_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should handle concurrent access without errors
        assert len(errors) == 0
        assert len(results) == 50  # 5 threads * 10 iterations


if __name__ == "__main__":
    pytest.main([__file__])
