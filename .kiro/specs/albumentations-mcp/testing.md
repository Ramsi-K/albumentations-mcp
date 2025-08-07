# Testing Strategy

This document outlines the comprehensive testing approach for the albumentations-mcp system, including unit tests, integration tests, mock data, and CI/CD pipeline configuration.

## Testing Framework Overview

### Test Structure

```
tests/
├── unit/
│   ├── test_parser.py           # Natural language parsing
│   ├── test_hooks.py            # Hook system execution
│   ├── test_verification.py     # LLM visual verification system
│   ├── test_serialization.py   # Pydantic model validation
│   └── test_transforms.py      # Albumentations integration
├── integration/
│   ├── test_mcp_protocol.py    # MCP compliance
│   ├── test_pipeline.py        # End-to-end workflows
│   ├── test_fallbacks.py       # Error handling scenarios
│   └── test_streaming.py       # Progressive responses
├── fixtures/
│   ├── images/                 # Test image samples
│   ├── prompts/                # Test prompt variations
│   └── responses/              # Expected response data
└── mocks/
    ├── verification.py         # Mock file operations and report generation
    ├── classifiers.py          # Mock classification results
    └── storage.py              # Mock file operations
```

## Unit Testing

### Natural Language Parser Tests (`test_parser.py`)

```python
import pytest
from albumentations_mcp.parser import PromptParser
from albumentations_mcp.models import TransformSpec

class TestPromptParser:
    @pytest.fixture
    def parser(self):
        return PromptParser()

    @pytest.mark.parametrize("prompt,expected_transforms", [
        ("add blur", [{"name": "Blur", "parameters": {"blur_limit": 15}}]),
        ("rotate 45 degrees", [{"name": "Rotate", "parameters": {"limit": 45}}]),
        ("make it brighter and flip", [
            {"name": "RandomBrightness", "parameters": {"brightness_limit": 0.2}},
            {"name": "HorizontalFlip", "parameters": {}}
        ]),
        ("blur heavily and add noise", [
            {"name": "Blur", "parameters": {"blur_limit": 50}},
            {"name": "GaussNoise", "parameters": {"var_limit": 30}}
        ])
    ])
    async def test_basic_parsing(self, parser, prompt, expected_transforms):
        result = await parser.parse_prompt(prompt)
        assert len(result.transforms) == len(expected_transforms)
        for actual, expected in zip(result.transforms, expected_transforms):
            assert actual.name == expected["name"]
            assert actual.parameters == expected["parameters"]

    @pytest.mark.parametrize("invalid_prompt", [
        "",  # Empty prompt
        "xyz123 invalid transform",  # Unknown transform
        "blur with limit 999",  # Invalid parameter range
        "rotate 720 degrees"  # Extreme parameter value
    ])
    async def test_invalid_prompts(self, parser, invalid_prompt):
        with pytest.raises(ValueError):
            await parser.parse_prompt(invalid_prompt)

    async def test_ambiguous_prompts(self, parser):
        """Test handling of ambiguous language"""
        result = await parser.parse_prompt("make it look better")
        # Should provide reasonable defaults
        assert len(result.transforms) > 0
        assert all(t.probability <= 1.0 for t in result.transforms)

    async def test_parameter_extraction(self, parser):
        """Test specific parameter extraction"""
        result = await parser.parse_prompt("blur with intensity 25")
        blur_transform = next(t for t in result.transforms if t.name == "Blur")
        assert blur_transform.parameters["blur_limit"] == 25
```

### Hook System Tests (`test_hooks.py`)

```python
import pytest
from albumentations_mcp.hooks import HookRegistry, HookContext, HookStage
from albumentations_mcp.models import ImagePayload

class TestHookSystem:
    @pytest.fixture
    def hook_registry(self):
        return HookRegistry()

    @pytest.fixture
    def sample_context(self):
        return HookContext(
            stage=HookStage.PRE_TRANSFORM,
            session_id="test-session",
            original_image=ImagePayload.from_base64("test-image-data")
        )

    def test_hook_registration(self, hook_registry):
        """Test hook registration with priorities"""
        @hook_registry.register_hook(
            stage="pre_transform",
            priority=10,
            critical=True
        )
        class TestHook:
            async def execute(self, context):
                return {"success": True}

        hooks = hook_registry.get_hooks("pre_transform")
        assert len(hooks) == 1
        assert hooks[0].priority == 10
        assert hooks[0].critical == True

    async def test_hook_execution_order(self, hook_registry, sample_context):
        """Test hooks execute in priority order"""
        execution_order = []

        @hook_registry.register_hook(stage="pre_transform", priority=20)
        class LowPriorityHook:
            async def execute(self, context):
                execution_order.append("low")
                return {"success": True}

        @hook_registry.register_hook(stage="pre_transform", priority=10)
        class HighPriorityHook:
            async def execute(self, context):
                execution_order.append("high")
                return {"success": True}

        await hook_registry.execute_hooks("pre_transform", sample_context)
        assert execution_order == ["high", "low"]

    async def test_critical_hook_failure(self, hook_registry, sample_context):
        """Test pipeline stops on critical hook failure"""
        @hook_registry.register_hook(
            stage="pre_transform",
            priority=10,
            critical=True
        )
        class FailingCriticalHook:
            async def execute(self, context):
                raise Exception("Critical failure")

        with pytest.raises(Exception, match="Critical failure"):
            await hook_registry.execute_hooks("pre_transform", sample_context)

    async def test_non_critical_hook_failure(self, hook_registry, sample_context):
        """Test pipeline continues on non-critical hook failure"""
        executed_hooks = []

        @hook_registry.register_hook(
            stage="pre_transform",
            priority=10,
            critical=False
        )
        class FailingHook:
            async def execute(self, context):
                raise Exception("Non-critical failure")

        @hook_registry.register_hook(
            stage="pre_transform",
            priority=20,
            critical=False
        )
        class SuccessHook:
            async def execute(self, context):
                executed_hooks.append("success")
                return {"success": True}

        results = await hook_registry.execute_hooks("pre_transform", sample_context)
        assert len(executed_hooks) == 1  # Success hook still executed
        assert any(not r.success for r in results)  # Failure recorded
```

### Model Interface Tests (`test_models.py`)

```python
import pytest
from albumentations_mcp.models import ImagePayload, TransformSpec, ProcessingResult
from albumentations_mcp.verification import VisualVerificationManager
from albumentations_mcp.analysis import ClassificationAnalyzer

class TestVisualVerificationManager:
    @pytest.fixture
    def verification_manager(self):
        return VisualVerificationManager()

    @pytest.fixture
    def sample_images(self):
        original = ImagePayload.from_base64("original-image-data")
        augmented = ImagePayload.from_base64("augmented-image-data")
        return original, augmented

    def test_save_images_for_review(self, verification_manager, sample_images):
        """Test saving images to temporary files for LLM review"""
        original, augmented = sample_images
        file_paths = verification_manager.save_images_for_review(
            original, augmented, "test_session_123"
        )

        assert "original" in file_paths
        assert "augmented" in file_paths
        assert file_paths["original"].endswith(".png")
        assert file_paths["augmented"].endswith(".png")

    def test_generate_verification_report(self, verification_manager):
        """Test generation of verification report for LLM review"""
        image_paths = {
            "original": "/tmp/original_123.png",
            "augmented": "/tmp/augmented_123.png"
        }

        report = verification_manager.generate_verification_report(
            image_paths, "add blur"
        )

        assert "original_123.png" in report
        assert "augmented_123.png" in report
        assert "add blur" in report
        assert "transformation success" in report.lower()

    def test_cleanup_temp_files(self, verification_manager, sample_images):
        """Test cleanup of temporary files after LLM review"""
        original, augmented = sample_images

        # Mock model failure
        analyzer.model.analyze = lambda *args: None

        result = await analyzer.analyze_transformation(
            original, augmented, "add blur"
        )
        assert result is None  # Graceful failure

class TestClassificationAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return ClassificationAnalyzer(model_name="mobilenet")

    async def test_classification_consistency(self, analyzer):
        """Test classification consistency checking"""
        image = ImagePayload.from_base64("test-image-data")

        original_result = await analyzer.classify_image(image)
        augmented_result = await analyzer.classify_image(image)  # Same image for test

        consistency = analyzer.compare_classifications(
            original_result, augmented_result
        )

        assert consistency.label_changed == False
        assert consistency.confidence_delta == 0.0
        assert consistency.risk_level == "low"
```

## Integration Testing

### MCP Protocol Compliance (`test_mcp_protocol.py`)

```python
import pytest
import json
from albumentations_mcp.server import AlbumentationsMCPServer

class TestMCPProtocol:
    @pytest.fixture
    async def mcp_server(self):
        # Setup with mock dependencies
        server = AlbumentationsMCPServer(
            session_manager=MockSessionManager(),
            model_registry=MockModelRegistry()
        )
        return server

    async def test_list_tools(self, mcp_server):
        """Test MCP list_tools compliance"""
        tools = await mcp_server.list_tools()

        assert isinstance(tools, list)
        assert len(tools) >= 3  # augment_image, list_transforms, validate_prompt

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert isinstance(tool["inputSchema"], dict)

    async def test_augment_image_tool_call(self, mcp_server):
        """Test augment_image tool execution"""
        arguments = {
            "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            "prompt": "add blur"
        }

        response = await mcp_server.call_tool("augment_image", arguments)

        assert "content" in response
        assert isinstance(response["content"], list)

        # Parse the JSON response
        result_data = json.loads(response["content"][0]["text"])
        assert "augmented_image" in result_data
        assert "applied_transforms" in result_data
        assert "success" in result_data
        assert result_data["success"] == True

    async def test_error_response_format(self, mcp_server):
        """Test MCP error response format"""
        # Invalid tool call
        response = await mcp_server.call_tool("invalid_tool", {})

        assert "isError" in response
        assert response["isError"] == True
        assert "content" in response
        assert isinstance(response["content"], list)
```

### End-to-End Pipeline Tests (`test_pipeline.py`)

```python
import pytest
from albumentations_mcp.pipeline import AugmentationPipeline
from albumentations_mcp.models import ImagePayload

class TestAugmentationPipeline:
    @pytest.fixture
    def pipeline(self):
        return AugmentationPipeline(
            session_manager=MockSessionManager(),
            model_registry=MockModelRegistry(),
            storage=MockStorage()
        )

    @pytest.fixture
    def test_image(self):
        # Load actual test image
        with open("tests/fixtures/images/sample.png", "rb") as f:
            image_data = f.read()
        return ImagePayload.from_bytes(image_data, "PNG")

    async def test_complete_pipeline(self, pipeline, test_image):
        """Test complete augmentation pipeline"""
        result = await pipeline.process(
            image=test_image,
            prompt="add blur and increase contrast",
            options={"enable_vision_verification": True}
        )

        # Verify processing result
        assert result.success == True
        assert len(result.applied_transforms) >= 2
        assert result.augmented_image is not None

        # Verify vision analysis
        assert result.vision_analysis is not None
        assert 1 <= result.vision_analysis.confidence_score <= 5

        # Verify metadata
        assert result.metadata["execution_time"] > 0
        assert "session_id" in result.metadata

    async def test_pipeline_with_failures(self, pipeline, test_image):
        """Test pipeline resilience to component failures"""
        # Mock vision model failure
        pipeline.model_registry.get_vision_model = lambda x: None

        result = await pipeline.process(
            image=test_image,
            prompt="add blur",
            options={"enable_vision_verification": True}
        )

        # Should still succeed without vision analysis
        assert result.success == True
        assert result.vision_analysis is None
        assert len(result.errors) > 0
```

## Mock Data and Fixtures

### Test Images (`fixtures/images/`)

```python
# Generate test images programmatically
import numpy as np
from PIL import Image
import base64

def create_test_images():
    """Create standardized test images"""

    # Simple solid color image
    solid_image = Image.new('RGB', (100, 100), color='red')

    # Gradient image
    gradient = np.linspace(0, 255, 100).astype(np.uint8)
    gradient_image = Image.fromarray(np.tile(gradient, (100, 1)))

    # Noise image
    noise = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    noise_image = Image.fromarray(noise)

    return {
        'solid': solid_image,
        'gradient': gradient_image,
        'noise': noise_image
    }
```

### Mock Vision Model Responses (`mocks/vision_models.py`)

```python
class MockVisionModel:
    def __init__(self, response_type="success"):
        self.response_type = response_type

    async def analyze_transformation(self, original, augmented, prompt):
        if self.response_type == "failure":
            raise Exception("Mock vision model failure")

        # Generate realistic mock response based on prompt
        if "blur" in prompt.lower():
            return AnalysisResult(
                confidence_score=4.0,
                explanation="Blur effect clearly applied to the image",
                visual_changes=["Reduced sharpness", "Smoothed details"],
                model_used="mock_vision",
                processing_time=0.5
            )

        return AnalysisResult(
            confidence_score=3.0,
            explanation="Transformation applied successfully",
            visual_changes=["Visual changes detected"],
            model_used="mock_vision",
            processing_time=0.5
        )
```

### Test Prompt Variations (`fixtures/prompts/`)

```yaml
# prompts/basic.yaml
basic_prompts:
  - prompt: 'add blur'
    expected_transforms: ['Blur']
    complexity: 1

  - prompt: 'make it brighter'
    expected_transforms: ['RandomBrightness']
    complexity: 1

  - prompt: 'rotate and flip'
    expected_transforms: ['Rotate', 'HorizontalFlip']
    complexity: 2

# prompts/complex.yaml
complex_prompts:
  - prompt: 'make it look vintage with sepia tones and film grain'
    expected_transforms:
      ['RandomBrightness', 'HueSaturationValue', 'GaussNoise']
    complexity: 8

  - prompt: 'create a dramatic effect with high contrast and slight blur'
    expected_transforms: ['RandomContrast', 'Blur']
    complexity: 6
```

## CI/CD Pipeline Configuration

### GitHub Actions Workflow (`.github/workflows/test.yml`)

```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run linting
        run: |
          black --check src/ tests/
          ruff check src/ tests/
          mypy src/

      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov=src/albumentations_mcp/ --cov-report=xml

      - name: Run integration tests
        run: |
          pytest tests/integration/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

      - name: Test MCP protocol compliance
        run: |
          python -m pytest tests/integration/test_mcp_protocol.py -v
```

### Coverage Requirements (`pytest.ini`)

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=90
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

## Performance Testing

### Load Testing (`test_performance.py`)

```python
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    @pytest.mark.slow
    async def test_concurrent_requests(self, mcp_server):
        """Test handling of concurrent requests"""
        async def make_request():
            return await mcp_server.call_tool("augment_image", {
                "image": "test-image-data",
                "prompt": "add blur"
            })

        # Test 10 concurrent requests
        start_time = time.time()
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # All requests should succeed
        assert all("isError" not in r for r in results)

        # Should complete within reasonable time
        assert end_time - start_time < 30  # 30 seconds max

    @pytest.mark.slow
    async def test_large_image_processing(self, mcp_server):
        """Test processing of large images"""
        # Create large test image (2048x2048)
        large_image = create_large_test_image()

        start_time = time.time()
        result = await mcp_server.call_tool("augment_image", {
            "image": large_image,
            "prompt": "add blur"
        })
        end_time = time.time()

        assert "isError" not in result
        assert end_time - start_time < 10  # Should complete within 10 seconds
```

This comprehensive testing strategy ensures the albumentations-mcp system is reliable, performant, and MCP-compliant across all components and use cases.
