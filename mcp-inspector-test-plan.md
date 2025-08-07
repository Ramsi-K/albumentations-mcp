# MCP Inspector Test Plan for Albumentations MCP Server

## Task 14.1: Test with MCP Inspector

**Status:** In Progress  
**Inspector URL:** http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=e1361c673d84df9e6fee95e2f9fe0a7013d56a220671a94e6f50de4fa65034fb#tools

### Test Requirements Coverage:

- ✅ 2.1: MCP protocol compliance and message formatting
- ✅ 2.2: Tool registration and discovery
- ✅ 2.3: Error handling and response formatting
- ✅ 2.4: Integration with MCP-compatible systems

---

## 1. Tool Discovery and Schema Validation

### Expected Tools:

- `augment_image` - Apply image augmentations based on natural language prompt
- `list_available_transforms` - List all available Albumentations transforms
- `validate_prompt` - Validate and preview transforms for a prompt
- `get_pipeline_status` - Get current pipeline status and registered hooks

### Test Steps:

1. **Navigate to Tools tab** in MCP Inspector
2. **Verify all 4 tools are discovered** and listed
3. **Check tool schemas** - each tool should have proper input/output schemas
4. **Validate descriptions** - ensure each tool has clear descriptions

### Expected Results:

- All 4 tools should be visible
- Each tool should have proper JSON schema for inputs
- Tool descriptions should be clear and helpful

---

## 2. Test All Tools with Various Input Combinations

### 2.1 Test `list_available_transforms`

**Input:** No parameters required
**Expected:** Returns list of available Albumentations transforms with descriptions

### 2.2 Test `get_pipeline_status`

**Input:** No parameters required
**Expected:** Returns pipeline status and hook information

### 2.3 Test `validate_prompt`

**Test Cases:**

- **Valid prompt:** `"add blur and rotate"`
  - Expected: `valid: true`, transforms found, confidence score
- **Empty prompt:** `""`
  - Expected: `valid: false`, appropriate error message
- **Invalid prompt:** `"xyzabc123 nonsense"`
  - Expected: `valid: false`, helpful suggestions

### 2.4 Test `augment_image`

**Test Cases:**

- **Valid image + simple prompt:**
  - `image_b64`: [Base64 encoded test image]
  - `prompt`: `"add blur"`
  - Expected: Returns augmented image as base64
- **Valid image + complex prompt:**
  - `image_b64`: [Base64 encoded test image]
  - `prompt`: `"add motion blur and increase contrast by 20%"`
  - Expected: Returns augmented image as base64
- **Invalid base64:**
  - `image_b64`: `"invalid_base64_data"`
  - `prompt`: `"add blur"`
  - Expected: Graceful error handling, returns original or error message

---

## 3. JSON-RPC Message Format Compliance

### Test Steps:

1. **Monitor Network tab** in browser dev tools while testing
2. **Verify request format** - all requests should be valid JSON-RPC 2.0
3. **Verify response format** - all responses should be valid JSON-RPC 2.0
4. **Check error handling** - errors should follow JSON-RPC error format

### Expected Format:

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {...}
  }
}

// Success Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {...}
}

// Error Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Error description"
  }
}
```

---

## 4. Prompt and Resource Discovery

### Test Steps:

1. **Check Prompts tab** in MCP Inspector
2. **Check Resources tab** in MCP Inspector
3. **Verify discovery mechanism** works correctly

### Expected Results:

- Currently no prompts or resources are implemented
- Discovery should work without errors
- Should return empty lists gracefully

---

## 5. Test Image Data

### Sample Base64 Image (100x100 red square):

```
iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAIAAAD/gAIDAAAAnklEQVR42u3QMQEAAAgDILV/51nBzwci0CmuRoEsWbJkyZKlQJYsWbJkyVIgS5YsWbJkKZAlS5YsWbIUyJIlS5YsWQpkyZIlS5YsBbJkyZIlS5YCWbJkyZIlS4EsWbJkyZKlQJYsWbJkyVIgS5YsWbJkKZAlS5YsWbIUyJIlS5YsWQpkyZIlS5YsBbJkyZIlS5YCWbK+LRQ9A47V9G9vAAAAAElFTkSuQmCC
```

---

## 6. Success Criteria

### ✅ Tool Discovery:

- [ ] All 4 expected tools are discovered
- [ ] Each tool has valid schema
- [ ] Tool descriptions are present and clear

### ✅ Tool Testing:

- [ ] `list_available_transforms` returns transform list
- [ ] `get_pipeline_status` returns pipeline info
- [ ] `validate_prompt` handles valid/invalid prompts correctly
- [ ] `augment_image` processes images and returns results

### ✅ Protocol Compliance:

- [ ] All messages follow JSON-RPC 2.0 format
- [ ] Error handling is graceful and informative
- [ ] Responses have correct structure

### ✅ Integration:

- [ ] Server connects successfully to MCP Inspector
- [ ] All operations work through the Inspector interface
- [ ] No protocol-level errors or crashes

---

## 7. How to Execute Tests

1. **Open MCP Inspector** at http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=e1361c673d84df9e6fee95e2f9fe0a7013d56a220671a94e6f50de4fa65034fb#tools

2. **Test Tool Discovery:**

   - Go to Tools tab
   - Verify all 4 tools are listed
   - Click on each tool to see its schema

3. **Test Each Tool:**

   - Select a tool from the list
   - Fill in the required parameters
   - Click "Call Tool"
   - Verify the response

4. **Test Error Cases:**

   - Try invalid inputs for each tool
   - Verify graceful error handling

5. **Monitor Protocol:**
   - Open browser dev tools (F12)
   - Watch Network tab during tool calls
   - Verify JSON-RPC format compliance

---

## 8. Documentation

After completing tests, document:

- Which tests passed/failed
- Any issues discovered
- Protocol compliance verification
- Recommendations for improvements
