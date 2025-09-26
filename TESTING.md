## Testing the MCP Server

This section describes how to test the deployed MCP server to ensure it's working correctly.

### Prerequisites

Before running the test, ensure you have:
- Python 3.7+ installed
- Required Python packages: `aiohttp`, `asyncio`, `json`
- A valid `mcp_tokens.json` file in the project root (generated after OAuth flow)

### Running the Test

Execute the working test script:

```bash
python test_mcp_fixed_session.py
```

### Expected Output

When the test runs successfully, you should see output similar to this:

```
🚀 Starting Fixed MCP Session Test
🔗 Base URL: https://apim-hvsvkzkl6s2ra.azure-api.net/mcp
🎫 Access Token: mcp_access_token_74f...

==================================================
📡 STEP 1: Establishing Persistent SSE Session
==================================================
🔗 Establishing SSE session to: https://apim-hvsvkzkl6s2ra.azure-api.net/mcp/sse
📡 SSE Response Status: 200
✅ SSE connection established with session URL

==================================================
🛠️  STEP 2: Sending tools/list Request (with active SSE)
==================================================
📤 Sending JSON-RPC request: {"jsonrpc": "2.0", "id": "test-request-1", "method": "tools/list"}
📨 Message Response Status: 202
📡 HTTP 202 received - listening for response on SSE stream...
✅ Found JSON-RPC response in SSE stream

==================================================
🔍 STEP 3: Analyzing Response  
==================================================
🛠️  Found 3 tools:
  • get_snippet: Retrieve a snippet by name.
  • hello_mcp: Hello world.
    ✅ Found hello_mcp tool!
  • save_snippet: Save a snippet with a name.

==================================================
🚀 STEP 4: Calling hello_mcp Tool
==================================================
📤 Sending JSON-RPC request: {"jsonrpc": "2.0", "id": "test-request-1", "method": "tools/call", "params": {"name": "hello_mcp", "arguments": {}}}
📨 Message Response Status: 202
📡 HTTP 202 received - listening for tool response on SSE stream...
✅ Found JSON-RPC response in SSE stream
✅ hello_mcp tool result: {'content': [{'type': 'text', 'text': 'Hello I am MCPTool!'}]}

🎉 SUCCESS: hello_mcp tool found and called successfully!
```

### What the Test Validates

The test performs the following validation steps:

1. **🔗 SSE Session Creation**: Establishes a Server-Sent Events connection and extracts the session-specific message URL
2. **🛠️ Tool Discovery**: Calls `tools/list` to discover available MCP tools 
3. **🔍 Tool Validation**: Confirms that the expected tools are available:
   - `hello_mcp`: Hello world demonstration tool
   - `get_snippet`: Retrieve code snippets from storage  
   - `save_snippet`: Save code snippets to storage
4. **🚀 Tool Execution**: Calls the `hello_mcp` tool and validates the response

### Available MCP Tools

The test will discover these MCP tools:

| Tool Name | Description | Purpose |
|-----------|-------------|---------|
| `hello_mcp` | Hello world. | Simple demonstration tool that returns a greeting |
| `get_snippet` | Retrieve a snippet by name. | Fetches stored code snippets from Azure Blob Storage |
| `save_snippet` | Save a snippet with a name. | Stores code snippets to Azure Blob Storage |

### Troubleshooting

If the test fails, check these common issues:

**❌ Authentication Errors (401)**
- Ensure `mcp_tokens.json` exists and contains valid OAuth tokens
- Verify the OAuth flow was completed successfully

**❌ SSE Connection Issues**
- Check that the Azure API Management service is running
- Verify network connectivity to the APIM endpoint

**❌ Tool Discovery Failures**
- Ensure Azure Functions are deployed and running
- Check Function App logs in Azure Portal for errors
- Verify APIM policies are correctly configured

**❌ Session Context Missing**  
- This usually indicates the SSE connection didn't establish properly
- The test will automatically retry and extract session URLs from the SSE stream

### Understanding the MCP Protocol Flow

The test demonstrates the proper MCP protocol implementation:

1. **Session Establishment**: SSE connection provides a session-specific message endpoint
2. **Async Communication**: JSON-RPC requests return HTTP 202 "Accepted" immediately  
3. **Response Streaming**: Actual responses arrive via the SSE stream as `event: message` data
4. **Session Management**: The session URL contains encrypted authentication context

This pattern ensures secure, scalable real-time communication between MCP clients and servers.