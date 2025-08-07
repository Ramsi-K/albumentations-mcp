"""Tests for the natural language parser module."""

import pytest
from src.albumentations_mcp.parser import (
    PromptParser,
    parse_prompt,
    validate_prompt,
    get_available_transforms,
    PromptParsingError,
    TransformType,
)


class TestPromptParser:
    """Test cases for PromptParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PromptParser()

    def test_simple_blur_parsing(self):
        """Test parsing simple blur command."""
        result = self.parser.parse_prompt("add blur")

        assert len(result.transforms) == 1
        assert result.transforms[0].name == TransformType.BLUR
        assert result.confidence > 0.8
        assert result.original_prompt == "add blur"

    def test_multiple_transforms(self):
        """Test parsing multiple transforms."""
        result = self.parser.parse_prompt("add blur and increase contrast")

        assert len(result.transforms) == 2
        transform_names = [t.name for t in result.transforms]
        assert TransformType.BLUR in transform_names
        assert TransformType.RANDOM_BRIGHTNESS_CONTRAST in transform_names

    def test_parameter_extraction(self):
        """Test parameter extraction from prompts."""
        result = self.parser.parse_prompt("rotate by 30 degrees")

        assert len(result.transforms) == 1
        assert result.transforms[0].name == TransformType.ROTATE
        assert result.transforms[0].parameters["limit"] == 30

    def test_blur_parameter_extraction(self):
        """Test blur parameter extraction."""
        result = self.parser.parse_prompt("blur by 5")

        assert len(result.transforms) == 1
        assert result.transforms[0].name == TransformType.BLUR
        assert result.transforms[0].parameters["blur_limit"] == 5

    def test_brightness_direction(self):
        """Test brightness increase/decrease detection."""
        # Test increase
        result = self.parser.parse_prompt("increase brightness")
        assert len(result.transforms) == 1
        assert (
            result.transforms[0].name
            == TransformType.RANDOM_BRIGHTNESS_CONTRAST
        )
        assert "brightness_limit" in result.transforms[0].parameters

        # Test decrease
        result = self.parser.parse_prompt("decrease brightness")
        assert len(result.transforms) == 1
        assert (
            result.transforms[0].name
            == TransformType.RANDOM_BRIGHTNESS_CONTRAST
        )
        assert "brightness_limit" in result.transforms[0].parameters

    def test_empty_prompt(self):
        """Test handling of empty prompts."""
        with pytest.raises(PromptParsingError):
            self.parser.parse_prompt("")

        with pytest.raises(PromptParsingError):
            self.parser.parse_prompt("   ")

    def test_invalid_prompt(self):
        """Test handling of invalid prompts."""
        with pytest.raises(PromptParsingError):
            self.parser.parse_prompt(None)

        with pytest.raises(PromptParsingError):
            self.parser.parse_prompt(123)

    def test_unrecognized_phrases(self):
        """Test handling of unrecognized phrases."""
        result = self.parser.parse_prompt("make it sparkly and add blur")

        # Should find blur but not sparkly
        assert len(result.transforms) == 1
        assert result.transforms[0].name == TransformType.BLUR
        assert len(result.warnings) > 0
        assert any("sparkly" in warning.lower() for warning in result.warnings)

    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        # All recognized
        result = self.parser.parse_prompt("blur and rotate")
        assert result.confidence == 1.0

        # Partially recognized
        result = self.parser.parse_prompt("blur and sparkle")
        assert 0 < result.confidence < 1.0

        # None recognized
        result = self.parser.parse_prompt("make it magical")
        assert result.confidence == 0.0

    def test_suggestions_for_unrecognized(self):
        """Test that suggestions are provided for unrecognized phrases."""
        result = self.parser.parse_prompt("make it blurry")

        # Should recognize "blurry" as blur
        assert len(result.transforms) == 1
        assert result.transforms[0].name == TransformType.BLUR

    def test_case_insensitive_parsing(self):
        """Test that parsing is case insensitive."""
        result1 = self.parser.parse_prompt("ADD BLUR")
        result2 = self.parser.parse_prompt("add blur")
        result3 = self.parser.parse_prompt("Add Blur")

        assert (
            len(result1.transforms)
            == len(result2.transforms)
            == len(result3.transforms)
            == 1
        )
        assert (
            result1.transforms[0].name
            == result2.transforms[0].name
            == result3.transforms[0].name
        )

    def test_get_available_transforms(self):
        """Test getting available transforms information."""
        transforms = self.parser.get_available_transforms()

        assert isinstance(transforms, dict)
        assert len(transforms) > 0

        # Check structure
        for transform_name, info in transforms.items():
            assert "description" in info
            assert "example_phrases" in info
            assert "default_parameters" in info
            assert "parameter_ranges" in info


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_parse_prompt_function(self):
        """Test parse_prompt convenience function."""
        result = parse_prompt("add blur")

        assert len(result.transforms) == 1
        assert result.transforms[0].name == TransformType.BLUR

    def test_validate_prompt_function(self):
        """Test validate_prompt convenience function."""
        result = validate_prompt("add blur and rotate")

        assert result["valid"] is True
        assert result["transforms_found"] == 2
        assert result["confidence"] > 0.8
        assert len(result["transforms"]) == 2

    def test_validate_prompt_invalid(self):
        """Test validate_prompt with invalid input."""
        result = validate_prompt("make it magical")

        assert result["valid"] is False
        assert result["transforms_found"] == 0
        assert result["confidence"] == 0.0
        assert len(result["warnings"]) > 0
        assert len(result["suggestions"]) > 0

    def test_get_available_transforms_function(self):
        """Test get_available_transforms convenience function."""
        transforms = get_available_transforms()

        assert isinstance(transforms, dict)
        assert len(transforms) > 0


class TestParameterExtraction:
    """Test parameter extraction for different transform types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PromptParser()

    def test_blur_limit_odd_numbers(self):
        """Test that blur limits are converted to odd numbers."""
        result = self.parser.parse_prompt("blur by 6")
        assert result.transforms[0].parameters["blur_limit"] == 7  # 6 -> 7

        result = self.parser.parse_prompt("blur by 5")
        assert (
            result.transforms[0].parameters["blur_limit"] == 5
        )  # Already odd

    def test_rotation_angle_limits(self):
        """Test rotation angle parameter limits."""
        result = self.parser.parse_prompt("rotate by 200 degrees")
        assert result.transforms[0].parameters["limit"] == 180  # Capped at 180

        result = self.parser.parse_prompt("rotate by 0.5 degrees")
        assert result.transforms[0].parameters["limit"] == 1  # Minimum 1

    def test_brightness_percentage_conversion(self):
        """Test brightness percentage conversion."""
        result = self.parser.parse_prompt("brightness by 50")
        assert (
            "brightness_limit" in result.transforms[0].parameters
            or "contrast_limit" in result.transforms[0].parameters
        )

    def test_crop_size_extraction(self):
        """Test crop size parameter extraction."""
        result = self.parser.parse_prompt("crop to 256x128")
        assert result.transforms[0].parameters["width"] == 256
        assert result.transforms[0].parameters["height"] == 128

        result = self.parser.parse_prompt("crop to 256")
        assert result.transforms[0].parameters["width"] == 256
        assert result.transforms[0].parameters["height"] == 256  # Square crop

    def test_noise_level_conversion(self):
        """Test noise level parameter conversion."""
        result = self.parser.parse_prompt("noise level 0.3")
        var_limit = result.transforms[0].parameters["var_limit"]
        assert isinstance(var_limit, tuple)
        assert len(var_limit) == 2
        assert var_limit[0] < var_limit[1]  # Range should be valid


if __name__ == "__main__":
    pytest.main([__file__])
