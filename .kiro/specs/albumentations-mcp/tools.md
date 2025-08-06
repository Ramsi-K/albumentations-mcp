# MCP Tool Specifications

This document defines the formal MCP tool interface specifications for the albumentations-mcp server, including exact schemas, capabilities, and execution contexts.

## Tool Registry

### Tool: `augment_image`

**MCP Tool Definition**:

```json
{
  "name": "augment_image",
  "description": "Apply image augmentations based on natural language descriptions. Processes an image through the Albumentations pipeline with optional vision verification and classification consistency checking.",
  "visibility": "public",
  "capabilities": [
    "image_processing",
    "natural_language_parsing",
    "vision_analysis"
  ],
  "inputSchema": {
    "type": "object",
    "properties": {
      "image": {
        "type": "string",
        "description": "Base64-encoded image data (PNG, JPEG, WEBP supported)",
        "format": "base64",
        "maxLength": 10485760
      },
      "prompt": {
        "type": "string",
        "description": "Natural language description of desired augmentations",
        "minLength": 1,
        "maxLength": 500,
        "examples": [
          "add motion blur and increase contrast",
          "rotate the image 15 degrees and add some noise",
          "make it brighter and flip horizontally",
          "apply gaussian blur with medium intensity"
        ]
      },
      "options": {
        "type": "object",
        "properties": {
          "enable_vision_verification": {
            "type": "boolean",
            "description": "Run vision model verification of transformation results",
            "default": true
          },
          "enable_classification_check": {
            "type": "boolean",
            "description": "Check classification consistency before/after augmentation",
            "default": true
          },
          "vision_model": {
            "type": "string",
            "description": "Vision model for verification analysis",
            "enum": ["claude", "gpt4v", "kiro"],
            "default": "claude"
          },
          "classifier_model": {
            "type": "string",
            "description": "Classification model for consistency checking",
            "enum": ["mobilenet", "cnn_explainer"],
            "default": "mobilenet"
          },
          "output_format": {
            "type": "string",
            "description": "Output image format",
            "enum": ["PNG", "JPEG", "WEBP"],
            "default": "PNG"
          },
          "quality": {
            "type": "integer",
            "description": "Output quality for JPEG (1-100)",
            "minimum": 1,
            "maximum": 100,
            "default": 95
          }
        },
        "additionalProperties": false
      },
      "auth_context": {
        "type": "object",
        "description": "Authentication and authorization context",
        "properties": {
          "user_id": { "type": "string" },
          "session_id": { "type": "string" },
          "permissions": { "type": "array", "items": { "type": "string" } }
        },
        "default": null
      }
    },
    "required": ["image", "prompt"],
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "augmented_image": {
        "type": "string",
        "description": "Base64-encoded augmented image",
        "format": "base64"
      },
      "applied_transforms": {
        "type": "array",
        "description": "Transforms successfully applied to the image",
        "items": {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "Albumentations transform name"
            },
            "parameters": {
              "type": "object",
              "description": "Parameters used for transform"
            },
            "probability": { "type": "number", "minimum": 0, "maximum": 1 },
            "execution_time": {
              "type": "number",
              "description": "Time taken to apply transform (seconds)"
            }
          },
          "required": ["name", "parameters", "probability"]
        }
      },
      "skipped_transforms": {
        "type": "array",
        "description": "Transforms that were parsed but skipped due to errors",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "reason": {
              "type": "string",
              "description": "Reason for skipping"
            },
            "error_code": { "type": "string" }
          }
        }
      },
      "metadata": {
        "type": "object",
        "properties": {
          "session_id": { "type": "string" },
          "execution_time": {
            "type": "number",
            "description": "Total processing time (seconds)"
          },
          "original_dimensions": {
            "type": "object",
            "properties": {
              "width": { "type": "integer" },
              "height": { "type": "integer" }
            }
          },
          "output_dimensions": {
            "type": "object",
            "properties": {
              "width": { "type": "integer" },
              "height": { "type": "integer" }
            }
          },
          "timestamp": { "type": "string", "format": "date-time" },
          "version": { "type": "string", "description": "Tool version" },
          "config_hash": {
            "type": "string",
            "description": "Configuration hash for reproducibility"
          }
        }
      },
      "vision_analysis": {
        "type": "object",
        "description": "Vision model verification results (if enabled)",
        "properties": {
          "confidence_score": {
            "type": "number",
            "minimum": 1,
            "maximum": 5,
            "description": "Confidence score 1-5 for transformation success"
          },
          "explanation": {
            "type": "string",
            "description": "Detailed explanation of observed changes"
          },
          "visual_changes": {
            "type": "array",
            "items": { "type": "string" },
            "description": "List of specific visual changes detected"
          },
          "model_used": { "type": "string" },
          "processing_time": { "type": "number" },
          "success": { "type": "boolean" }
        }
      },
      "classification_analysis": {
        "type": "object",
        "description": "Classification consistency results (if enabled)",
        "properties": {
          "label_changed": { "type": "boolean" },
          "confidence_delta": { "type": "number" },
          "original_prediction": {
            "type": "object",
            "properties": {
              "class": { "type": "string" },
              "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
              "top_k": { "type": "array", "items": { "type": "object" } }
            }
          },
          "augmented_prediction": {
            "type": "object",
            "properties": {
              "class": { "type": "string" },
              "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
              "top_k": { "type": "array", "items": { "type": "object" } }
            }
          },
          "risk_level": { "type": "string", "enum": ["low", "medium", "high"] },
          "consistency_score": { "type": "number", "minimum": 0, "maximum": 1 },
          "model_used": { "type": "string" },
          "processing_time": { "type": "number" }
        }
      },
      "success": { "type": "boolean" },
      "errors": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "stage": {
              "type": "string",
              "description": "Processing stage where error occurred"
            },
            "message": { "type": "string" },
            "severity": {
              "type": "string",
              "enum": ["warning", "error", "critical"]
            },
            "error_code": { "type": "string" },
            "timestamp": { "type": "string", "format": "date-time" }
          }
        }
      }
    },
    "required": ["augmented_image", "applied_transforms", "metadata", "success"]
  }
}
```

### Tool: `list_available_transforms`

**MCP Tool Definition**:

```json
{
  "name": "list_available_transforms",
  "description": "List all available Albumentations transforms with their parameters, descriptions, and usage examples.",
  "visibility": "public",
  "capabilities": ["metadata_query"],
  "inputSchema": {
    "type": "object",
    "properties": {
      "category": {
        "type": "string",
        "description": "Filter transforms by category",
        "enum": ["blur", "brightness", "contrast", "geometric", "noise", "all"],
        "default": "all"
      },
      "include_examples": {
        "type": "boolean",
        "description": "Include usage examples for each transform",
        "default": true
      }
    },
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "transforms": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "category": { "type": "string" },
            "description": { "type": "string" },
            "parameters": {
              "type": "object",
              "description": "Parameter schema with types and ranges"
            },
            "examples": {
              "type": "array",
              "items": { "type": "string" },
              "description": "Natural language usage examples"
            },
            "aliases": {
              "type": "array",
              "items": { "type": "string" },
              "description": "Alternative names users might use"
            }
          }
        }
      },
      "total_count": { "type": "integer" },
      "categories": { "type": "array", "items": { "type": "string" } }
    }
  }
}
```

### Tool: `validate_prompt`

**MCP Tool Definition**:

```json
{
  "name": "validate_prompt",
  "description": "Validate and parse a natural language prompt without processing an image. Useful for debugging and previewing transform pipelines.",
  "visibility": "public",
  "capabilities": ["natural_language_parsing", "validation"],
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": {
        "type": "string",
        "description": "Natural language prompt to validate",
        "minLength": 1,
        "maxLength": 500
      },
      "strict_mode": {
        "type": "boolean",
        "description": "Enable strict validation (reject ambiguous prompts)",
        "default": false
      }
    },
    "required": ["prompt"],
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "parsed_transforms": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "parameters": { "type": "object" },
            "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
          }
        }
      },
      "validation_errors": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "message": { "type": "string" },
            "severity": { "type": "string", "enum": ["warning", "error"] },
            "suggestion": { "type": "string" }
          }
        }
      },
      "suggestions": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Suggestions for improving the prompt"
      },
      "ambiguities": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "text": { "type": "string", "description": "Ambiguous phrase" },
            "interpretations": {
              "type": "array",
              "items": { "type": "string" }
            }
          }
        }
      },
      "estimated_execution_time": { "type": "number" },
      "complexity_score": { "type": "number", "minimum": 1, "maximum": 10 }
    }
  }
}
```

## Authorization Context

### Authentication Schema

```json
{
  "auth_context": {
    "type": "object",
    "properties": {
      "user_id": {
        "type": "string",
        "description": "Unique user identifier"
      },
      "session_id": {
        "type": "string",
        "description": "Session identifier for request tracking"
      },
      "permissions": {
        "type": "array",
        "items": { "type": "string" },
        "description": "User permissions",
        "examples": [["augment_image", "list_transforms", "validate_prompt"]]
      },
      "rate_limit": {
        "type": "object",
        "properties": {
          "requests_per_minute": { "type": "integer", "default": 60 },
          "concurrent_requests": { "type": "integer", "default": 5 }
        }
      },
      "resource_limits": {
        "type": "object",
        "properties": {
          "max_image_size": {
            "type": "integer",
            "description": "Max image size in bytes"
          },
          "max_processing_time": {
            "type": "integer",
            "description": "Max processing time in seconds"
          }
        }
      }
    }
  }
}
```

### Permission Levels

- **`augment_image`**: Can process images with augmentations
- **`list_transforms`**: Can query available transforms
- **`validate_prompt`**: Can validate prompts
- **`admin`**: Full access including system configuration

## Streaming and Progressive Results

### Streaming Response Schema

```json
{
  "streaming_response": {
    "type": "object",
    "properties": {
      "event_type": {
        "type": "string",
        "enum": ["progress", "stage_complete", "error", "final_result"]
      },
      "stage": { "type": "string" },
      "progress": { "type": "number", "minimum": 0, "maximum": 1 },
      "message": { "type": "string" },
      "data": { "type": "object" },
      "timestamp": { "type": "string", "format": "date-time" }
    }
  }
}
```

### Progressive Update Events

```json
[
  {
    "event_type": "progress",
    "stage": "parsing",
    "progress": 0.1,
    "message": "Parsing natural language prompt"
  },
  {
    "event_type": "stage_complete",
    "stage": "parsing",
    "progress": 0.2,
    "data": { "transforms_found": 3 }
  },
  {
    "event_type": "progress",
    "stage": "processing",
    "progress": 0.5,
    "message": "Applying transform 2 of 3"
  },
  {
    "event_type": "progress",
    "stage": "verification",
    "progress": 0.8,
    "message": "Running vision analysis"
  },
  {
    "event_type": "final_result",
    "stage": "complete",
    "progress": 1.0,
    "data": { "result": "..." }
  }
]
```

## File I/O Interface

### Image Input Formats

**Supported Input Methods**:

1. **Base64 Encoded**: Direct embedding in MCP request
2. **File Path**: Local file system path (for local deployments)
3. **URL**: HTTP/HTTPS image URL (with validation)
4. **Binary Upload**: Raw binary data with content-type header

**Input Validation**:

```python
class ImageInputValidator:
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    SUPPORTED_FORMATS = ["PNG", "JPEG", "WEBP", "TIFF"]

    def validate_input(self, image_data: str, format_hint: str = None) -> ImagePayload:
        # Validate size, format, and content
        pass
```

### Output Management

**Output Locations**:

- **MCP Response**: Base64-encoded result in response
- **Session Storage**: Files saved to `outputs/{session_id}/`
- **Temporary Files**: Cleaned up after response sent

**File Naming Convention**:

```
outputs/{session_id}/
├── original.{ext}           # Original input image
├── result.{ext}             # Final augmented image
├── metadata.json            # Transform metadata
├── visual_verification.md   # Vision analysis report
├── classification_report.json # Classification consistency
└── config.json             # Reproducible configuration
```

## Error Handling Behavior

### Error Response Format

```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Error message with details"
    }
  ],
  "error_details": {
    "error_code": "TRANSFORM_FAILED",
    "stage": "image_processing",
    "message": "Blur transform failed: invalid blur_limit value",
    "severity": "error",
    "recoverable": true,
    "suggestions": ["Try blur_limit between 3 and 100"]
  }
}
```

### Error Codes

- **`PARSE_ERROR`**: Natural language parsing failed
- **`INVALID_IMAGE`**: Image format or size issues
- **`TRANSFORM_FAILED`**: Albumentations transform error
- **`MODEL_UNAVAILABLE`**: Vision/classification model error
- **`PERMISSION_DENIED`**: Authorization failure
- **`RATE_LIMITED`**: Too many requests
- **`TIMEOUT`**: Processing timeout exceeded

### Hook Error Behavior

**Critical Hooks**: Stop pipeline execution

- `pre_mcp`: Input validation
- `pre_transform`: Image validation

**Non-Critical Hooks**: Log error and continue

- `post_transform_verify`: Vision analysis
- `post_transform_classify`: Classification check
- `post_save`: Cleanup operations

## Tool Chaining Support

### Chain-Aware Responses

Tools can indicate they support chaining:

```json
{
  "supports_chaining": true,
  "chain_suggestions": [
    {
      "next_tool": "augment_image",
      "reason": "Apply the validated transforms",
      "parameters": { "prompt": "validated_prompt_here" }
    }
  ]
}
```

### Example Tool Chain

1. **Discovery**: `list_available_transforms()` → Show capabilities
2. **Validation**: `validate_prompt("make it vintage")` → Parse and validate
3. **Execution**: `augment_image(image, "make it vintage")` → Apply transforms
4. **Iteration**: `augment_image(result, "increase brightness")` → Refine result

This formal tool specification provides the complete MCP interface definition needed for integration with Kiro and other MCP orchestrators.
