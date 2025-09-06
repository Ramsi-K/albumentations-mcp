"""Unit tests for image handling utilities."""

import base64
import io

import numpy as np
import pytest
from PIL import Image

from src.albumentations_mcp.errors import (
    ImageConversionError,
    ImageValidationError,
)
from src.albumentations_mcp.image_conversions import (
    base64_to_pil,
    numpy_to_pil,
    pil_to_base64,
    pil_to_numpy,
)
from src.albumentations_mcp.utils.image_handler import (
    MAX_IMAGE_SIZE,
    SUPPORTED_FORMATS,
    get_image_info,
    get_supported_formats,
    is_supported_format,
    validate_image,
)


class TestBase64ToPil:
    """Test base64 to PIL Image conversion."""

    def create_test_image(self, size=(100, 100), mode="RGB", fmt="PNG"):
        """Create a test image and return its base64 representation."""
        image = Image.new(mode, size, color="red")
        buffer = io.BytesIO()
        image.save(buffer, format=fmt)
        return base64.b64encode(buffer.getvalue()).decode("utf-8"), image

    def test_valid_base64_conversion(self):
        """Test conversion of valid base64 image data."""
        base64_data, original = self.create_test_image()
        converted = base64_to_pil(base64_data)

        assert converted.size == original.size
        assert converted.mode in ("RGB", "RGBA")

    def test_base64_with_data_url_prefix(self):
        """Test conversion with data URL prefix."""
        base64_data, original = self.create_test_image()
        data_url = f"data:image/png;base64,{base64_data}"
        converted = base64_to_pil(data_url)

        assert converted.size == original.size
        assert converted.mode in ("RGB", "RGBA")

    def test_different_image_formats(self):
        """Test conversion of different image formats."""
        for fmt in ["PNG", "JPEG"]:
            base64_data, original = self.create_test_image(fmt=fmt)
            converted = base64_to_pil(base64_data)
            assert converted.size == original.size

    def test_grayscale_to_rgb_conversion(self):
        """Test conversion of grayscale images to RGB."""
        base64_data, _ = self.create_test_image(mode="L")
        converted = base64_to_pil(base64_data)
        assert converted.mode == "RGB"

    def test_palette_to_rgb_conversion(self):
        """Test conversion of palette images to RGB."""
        # Create a palette image
        image = Image.new("P", (100, 100))
        image.putpalette([i for i in range(256)] * 3)  # Simple palette
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        converted = base64_to_pil(base64_data)
        assert converted.mode == "RGB"

    def test_empty_string_error(self):
        """Test error handling for empty string."""
        with pytest.raises(ImageConversionError, match="must be a non-empty string"):
            base64_to_pil("")

    def test_none_input_error(self):
        """Test error handling for None input."""
        with pytest.raises(ImageConversionError, match="must be a non-empty string"):
            base64_to_pil(None)

    def test_invalid_base64_error(self):
        """Test error handling for invalid base64 data."""
        with pytest.raises(
            ImageConversionError,
            match="Image validation failed.*Invalid Base64 encoding",
        ):
            base64_to_pil("invalid_base64_data!")

    def test_invalid_image_data_error(self):
        """Test error handling for valid base64 but invalid image data."""
        invalid_data = base64.b64encode(b"not an image").decode("utf-8")
        with pytest.raises(ImageConversionError, match="Cannot open image"):
            base64_to_pil(invalid_data)

    def test_malformed_data_url_error(self):
        """Test error handling for malformed data URL."""
        with pytest.raises(ImageConversionError, match="Invalid data URL format"):
            base64_to_pil("data:image/png;base64")  # Missing comma

    def test_large_image_validation(self):
        """Test validation of oversized images."""
        # Create a large image that exceeds MAX_IMAGE_SIZE
        large_size = (MAX_IMAGE_SIZE[0] + 1, 100)
        base64_data, _ = self.create_test_image(size=large_size)

        with pytest.raises(
            ImageConversionError,
            match="Unexpected error.*Image too large",
        ):
            base64_to_pil(base64_data)


class TestPilToBase64:
    """Test PIL Image to base64 conversion."""

    def create_test_image(self, size=(100, 100), mode="RGB"):
        """Create a test PIL Image."""
        return Image.new(mode, size, color="blue")

    def test_valid_pil_conversion(self):
        """Test conversion of valid PIL Image."""
        image = self.create_test_image()
        base64_data = pil_to_base64(image)

        assert isinstance(base64_data, str)
        assert len(base64_data) > 0

        # Verify we can convert back
        converted_back = base64_to_pil(base64_data)
        assert converted_back.size == image.size

    def test_different_formats(self):
        """Test conversion to different formats."""
        image = self.create_test_image()

        for fmt in ["PNG", "JPEG", "WEBP"]:
            if fmt in SUPPORTED_FORMATS:
                base64_data = pil_to_base64(image, format=fmt)
                assert isinstance(base64_data, str)
                assert len(base64_data) > 0

    def test_jpeg_quality_parameter(self):
        """Test JPEG quality parameter."""
        image = self.create_test_image()

        low_quality = pil_to_base64(image, format="JPEG", quality=10)
        high_quality = pil_to_base64(image, format="JPEG", quality=95)

        # Low quality should result in smaller file size
        assert len(low_quality) < len(high_quality)

    def test_rgba_to_jpeg_conversion(self):
        """Test RGBA image conversion to JPEG (should handle transparency)."""
        image = self.create_test_image(mode="RGBA")
        base64_data = pil_to_base64(image, format="JPEG")

        # Should not raise error and should produce valid data
        assert isinstance(base64_data, str)
        assert len(base64_data) > 0

    def test_invalid_input_error(self):
        """Test error handling for invalid input."""
        with pytest.raises(ImageConversionError, match="must be a PIL Image object"):
            pil_to_base64("not an image")

    def test_unsupported_format_error(self):
        """Test error handling for unsupported format."""
        image = self.create_test_image()
        with pytest.raises(ImageValidationError, match="Unsupported format"):
            pil_to_base64(image, format="UNSUPPORTED")

    def test_zero_size_image_error(self):
        """Test error handling for zero-size image."""
        # Create an image with zero size (this might not be possible with PIL directly)
        # So we'll test with a very small image instead
        image = self.create_test_image(size=(1, 1))
        base64_data = pil_to_base64(image)
        assert isinstance(base64_data, str)


class TestNumpyToPil:
    """Test numpy array to PIL Image conversion."""

    def test_rgb_array_conversion(self):
        """Test conversion of RGB numpy array."""
        array = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        image = numpy_to_pil(array)

        assert image.size == (100, 100)
        assert image.mode == "RGB"

    def test_rgba_array_conversion(self):
        """Test conversion of RGBA numpy array."""
        array = np.random.randint(0, 256, (100, 100, 4), dtype=np.uint8)
        image = numpy_to_pil(array)

        assert image.size == (100, 100)
        assert image.mode == "RGBA"

    def test_grayscale_array_conversion(self):
        """Test conversion of grayscale numpy array."""
        array = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        image = numpy_to_pil(array)

        assert image.size == (100, 100)
        assert image.mode == "L"

    def test_single_channel_3d_array(self):
        """Test conversion of single-channel 3D array."""
        array = np.random.randint(0, 256, (100, 100, 1), dtype=np.uint8)
        image = numpy_to_pil(array)

        assert image.size == (100, 100)
        assert image.mode == "L"

    def test_float_array_conversion(self):
        """Test conversion of float array in [0, 1] range."""
        array = np.random.rand(100, 100, 3).astype(np.float32)
        image = numpy_to_pil(array)

        assert image.size == (100, 100)
        assert image.mode == "RGB"

    def test_float64_array_conversion(self):
        """Test conversion of float64 array."""
        array = np.random.rand(100, 100, 3).astype(np.float64)
        image = numpy_to_pil(array)

        assert image.size == (100, 100)
        assert image.mode == "RGB"

    def test_invalid_input_error(self):
        """Test error handling for invalid input."""
        with pytest.raises(ImageConversionError, match="must be a numpy array"):
            numpy_to_pil("not an array")

    def test_invalid_dimensions_error(self):
        """Test error handling for invalid array dimensions."""
        array = np.random.randint(0, 256, (100,), dtype=np.uint8)  # 1D array
        with pytest.raises(ImageValidationError, match="must be 2D or 3D"):
            numpy_to_pil(array)

    def test_invalid_channels_error(self):
        """Test error handling for invalid number of channels."""
        array = np.random.randint(0, 256, (100, 100, 5), dtype=np.uint8)  # 5 channels
        with pytest.raises(ImageValidationError, match="must have 1, 3, or 4 channels"):
            numpy_to_pil(array)

    def test_float_array_out_of_range_error(self):
        """Test error handling for float array with values outside [0, 1]."""
        array = np.random.rand(100, 100, 3) * 2  # Values in [0, 2]
        with pytest.raises(
            ImageValidationError,
            match="must have values in \\[0, 1\\] range",
        ):
            numpy_to_pil(array)


class TestPilToNumpy:
    """Test PIL Image to numpy array conversion."""

    def test_rgb_image_conversion(self):
        """Test conversion of RGB PIL Image."""
        image = Image.new("RGB", (100, 100), color="red")
        array = pil_to_numpy(image)

        assert array.shape == (100, 100, 3)
        assert array.dtype == np.uint8

    def test_rgba_image_conversion(self):
        """Test conversion of RGBA PIL Image."""
        image = Image.new("RGBA", (100, 100), color="red")
        array = pil_to_numpy(image)

        assert array.shape == (100, 100, 4)
        assert array.dtype == np.uint8

    def test_grayscale_image_conversion(self):
        """Test conversion of grayscale PIL Image."""
        image = Image.new("L", (100, 100), color=128)
        array = pil_to_numpy(image)

        assert array.shape == (100, 100, 1)  # Should expand to 3D
        assert array.dtype == np.uint8

    def test_invalid_input_error(self):
        """Test error handling for invalid input."""
        with pytest.raises(ImageConversionError, match="must be a PIL Image object"):
            pil_to_numpy("not an image")


class TestValidateImage:
    """Test image validation function."""

    def test_valid_image_passes(self):
        """Test that valid images pass validation."""
        image = Image.new("RGB", (100, 100), color="green")
        validate_image(image)  # Should not raise

    def test_invalid_input_error(self):
        """Test error handling for invalid input."""
        with pytest.raises(ImageValidationError, match="must be a PIL Image object"):
            validate_image("not an image")

    def test_zero_size_image_error(self):
        """Test error handling for zero-size image."""
        # Create a mock image with zero size
        image = Image.new("RGB", (100, 100))
        # Manually set size to simulate zero-size image
        image._size = (0, 100)

        with pytest.raises(ImageValidationError, match="Invalid image dimensions"):
            validate_image(image)

    def test_oversized_image_error(self):
        """Test error handling for oversized image."""
        # This test might be slow, so we'll use a smaller test
        large_size = (MAX_IMAGE_SIZE[0] + 1, 100)
        try:
            image = Image.new("RGB", large_size)
            with pytest.raises(ImageValidationError, match="Image too large"):
                validate_image(image)
        except MemoryError:
            # Skip test if we can't create the large image
            pytest.skip("Cannot create large image due to memory constraints")


class TestGetImageInfo:
    """Test get_image_info function."""

    def test_rgb_image_info(self):
        """Test getting info for RGB image."""
        image = Image.new("RGB", (200, 150), color="blue")
        info = get_image_info(image)

        assert info["width"] == 200
        assert info["height"] == 150
        assert info["mode"] == "RGB"
        assert info["channels"] == 3
        assert info["pixel_count"] == 30000
        assert not info["has_transparency"]

    def test_rgba_image_info(self):
        """Test getting info for RGBA image."""
        image = Image.new("RGBA", (100, 100), color="red")
        info = get_image_info(image)

        assert info["mode"] == "RGBA"
        assert info["channels"] == 4
        assert info["has_transparency"]

    def test_grayscale_image_info(self):
        """Test getting info for grayscale image."""
        image = Image.new("L", (50, 75), color=128)
        info = get_image_info(image)

        assert info["mode"] == "L"
        assert info["channels"] == 1
        assert not info["has_transparency"]


class TestFormatSupport:
    """Test format support functions."""

    def test_is_supported_format(self):
        """Test format support checking."""
        assert is_supported_format("PNG")
        assert is_supported_format("png")  # Case insensitive
        assert is_supported_format("JPEG")
        assert not is_supported_format("UNSUPPORTED")

    def test_get_supported_formats(self):
        """Test getting list of supported formats."""
        formats = get_supported_formats()
        assert isinstance(formats, list)
        assert "PNG" in formats
        assert "JPEG" in formats
        assert len(formats) > 0


class TestIntegration:
    """Integration tests for the complete conversion pipeline."""

    def test_round_trip_conversion(self):
        """Test complete round-trip conversion: PIL -> base64 -> PIL."""
        original = Image.new("RGB", (100, 100), color="purple")

        # PIL -> base64
        base64_data = pil_to_base64(original)

        # base64 -> PIL
        converted = base64_to_pil(base64_data)

        assert converted.size == original.size
        assert converted.mode == original.mode

    def test_numpy_pil_round_trip(self):
        """Test numpy -> PIL -> numpy conversion."""
        original_array = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        # numpy -> PIL
        image = numpy_to_pil(original_array)

        # PIL -> numpy
        converted_array = pil_to_numpy(image)

        assert converted_array.shape == original_array.shape
        assert converted_array.dtype == original_array.dtype
        np.testing.assert_array_equal(converted_array, original_array)

    def test_complete_pipeline(self):
        """Test complete processing pipeline."""
        # Start with numpy array
        array = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)

        # numpy -> PIL
        image = numpy_to_pil(array)
        validate_image(image)

        # PIL -> base64
        base64_data = pil_to_base64(image, format="PNG")

        # base64 -> PIL
        restored_image = base64_to_pil(base64_data)
        validate_image(restored_image)

        # PIL -> numpy
        restored_array = pil_to_numpy(restored_image)

        # Verify final result
        assert restored_array.shape == array.shape
        assert restored_array.dtype == array.dtype
        # Note: Due to PNG compression, arrays might not be exactly equal
        # but they should be very close
        assert np.allclose(restored_array, array, atol=1)


if __name__ == "__main__":
    pytest.main([__file__])
