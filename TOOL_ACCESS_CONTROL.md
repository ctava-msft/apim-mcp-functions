# Tool-Level Access Control Implementation

This document describes the fine-grained tool access control implementation for the MCP server.

## Overview

The MCP server now implements role-based access control (RBAC) at the API Gateway level, ensuring users can only access tools they have permission to use. This prevents unauthorized tool discovery and execution.

## Architecture

```
User/Agent Request
    ↓
[APIM Policy - Inbound]
    ├─ Extract roles from Entra ID token
    ├─ Map roles to allowed tools
    ├─ Validate tools/call requests ← PREVENTS UNAUTHORIZED EXECUTION
    ↓
[Azure Functions Backend] ← Only reached if authorized
    ↓
[APIM Policy - Outbound]
    └─ Filter tools/list response ← HIDE UNAUTHORIZED TOOLS
    ↓
Response to User/Agent
```

## Built-in Roles

| Role | Allowed Tools | Use Case |
|------|--------------|----------|
| **admin** | hello_mcp, get_snippet, save_snippet | Full administrative access |
| **writer** | hello_mcp, get_snippet, save_snippet | Read and write access |
| **reader** | hello_mcp, get_snippet | Read-only access |
| **user** | hello_mcp | Minimal access (default) |

## How It Works

### 1. Role Extraction (Inbound)

When a request arrives with a Bearer token:

```csharp
// Extract JWT token from Entra ID cache
JObject tokenData = JObject.Parse(accessToken);
string accessTokenStr = tokenData["access_token"]?.ToString();

// Parse JWT payload (second part after '.')
string[] tokenParts = accessTokenStr.Split('.');
string payload = tokenParts[1];

// Decode and parse payload
JObject payloadObj = JObject.Parse(payloadJson);

// Extract roles and groups
// Both 'roles' and 'groups' claims are combined
if (payloadObj["roles"] != null) {
    // Add app roles
}
if (payloadObj["groups"] != null) {
    // Add group memberships
}

// Default to 'user' role if no roles found
```

### 2. Permission Mapping (Inbound)

The policy maintains a role-to-tools mapping:

```csharp
JObject mapping = new JObject();

// Admin: all tools
JArray adminTools = new JArray();
adminTools.Add("hello_mcp");
adminTools.Add("get_snippet");
adminTools.Add("save_snippet");
mapping["admin"] = adminTools;

// Writer: read/write tools
JArray writerTools = new JArray();
writerTools.Add("hello_mcp");
writerTools.Add("get_snippet");
writerTools.Add("save_snippet");
mapping["writer"] = writerTools;

// Reader: read-only tools
JArray readerTools = new JArray();
readerTools.Add("hello_mcp");
readerTools.Add("get_snippet");
mapping["reader"] = readerTools;

// User: minimal access
JArray userTools = new JArray();
userTools.Add("hello_mcp");
mapping["user"] = userTools;
```

### 3. tools/call Validation (Inbound)

Before reaching the backend, tools/call requests are validated:

```csharp
// Extract requested tool name
string requestedTool = request["params"]["name"].ToString();

// Check if user has permission
bool isToolAllowed = false;
foreach (var tool in allowedTools) {
    if (tool.ToString() == requestedTool) {
        isToolAllowed = true;
        break;
    }
}

// Return 403 if not allowed (BEFORE backend execution)
if (!isToolAllowed) {
    return {
        "jsonrpc": "2.0",
        "id": requestId,
        "error": {
            "code": -32001,
            "message": "Access denied: Tool 'X' is not available for your role(s)"
        }
    };
}
```

### 4. tools/list Filtering (Outbound)

After the backend returns the full list of tools, filter to show only allowed ones:

```csharp
// Parse backend response
JObject response = JObject.Parse(responseBody);
JArray allTools = response["result"]["tools"];

// Filter based on permissions
JArray filteredTools = new JArray();
foreach (var tool in allTools) {
    string toolName = tool["name"].ToString();
    if (allowedTools.Contains(toolName)) {
        filteredTools.Add(tool);
    }
}

// Replace with filtered list
response["result"]["tools"] = filteredTools;
```

## Configuration

### Entra ID Setup

1. **Create App Roles**:
   - Navigate to Azure Portal → Entra ID → App Registrations
   - Select your app → App roles
   - Create roles: `admin`, `writer`, `reader`
   - Set allowed member types (Users/Groups)

2. **Assign Users to Roles**:
   - Navigate to Enterprise Applications
   - Select your application
   - Users and groups → Add user/group
   - Select role assignment

3. **Configure Token Claims**:
   - Ensure the `roles` claim is included in the token
   - Optionally enable `groups` claim for group-based access

### Using Group Memberships

If you prefer to use Entra ID security groups:

1. **Enable groups claim** in token configuration
2. **Map group GUIDs to role names** in the policy:

```xml
<set-variable name="roleToolMapping" value="@{
    JObject mapping = new JObject();
    
    // Map group GUID to admin role
    JArray adminTools = new JArray();
    adminTools.Add("hello_mcp");
    adminTools.Add("get_snippet");
    adminTools.Add("save_snippet");
    mapping["12345678-1234-1234-1234-123456789abc"] = adminTools;  // Admin group GUID
    
    // Map group GUID to reader role
    JArray readerTools = new JArray();
    readerTools.Add("hello_mcp");
    readerTools.Add("get_snippet");
    mapping["87654321-4321-4321-4321-cba987654321"] = readerTools;  // Reader group GUID
    
    return mapping;
}" />
```

### Adding Custom Tools

When you add a new tool to `function_app.py`:

1. Update the role-to-tools mapping in `mcp-api.policy.xml`:

```xml
<set-variable name="roleToolMapping" value="@{
    JObject mapping = new JObject();
    
    JArray adminTools = new JArray();
    adminTools.Add("hello_mcp");
    adminTools.Add("get_snippet");
    adminTools.Add("save_snippet");
    adminTools.Add("your_new_tool");  // Add here
    mapping["admin"] = adminTools;
    
    // Configure for other roles as needed...
    
    return mapping;
}" />
```

2. Deploy the updated policy:

```bash
azd deploy
```

## Security Considerations

### Principle of Least Privilege

- Users without explicit role assignments default to the `user` role
- The `user` role has minimal permissions (hello_mcp only)
- Assign roles based on job functions

### Defense in Depth

1. **Inbound validation**: Prevents unauthorized backend calls
2. **Outbound filtering**: Hides unauthorized tools from discovery
3. **JSON-RPC compliance**: Proper error messages for clients
4. **Audit trail**: All access attempts are logged by APIM

### Group GUID Validation

When using the `groups` claim:
- Group UUIDs must be explicitly mapped to role names
- Unknown groups don't grant access (treated as `user` role)
- This prevents privilege escalation via group membership

## Testing

### Access Control Test

Run the comprehensive test suite:

```bash
# Set your APIM endpoint
export MCP_BASE_URL=https://your-apim.azure-api.net/mcp

# Run the test
python test_tool_access_control.py
```

The test validates:
- ✅ tools/list returns only permitted tools
- ✅ Authorized tools/call requests succeed
- ✅ Unauthorized tools/call requests return 403 Forbidden
- ✅ Error responses include proper JSON-RPC formatting

### Expected Results

**For a user with 'reader' role:**

```bash
# tools/list returns only hello_mcp and get_snippet
✅ tools/list returned 2 tools based on user permissions:
  • hello_mcp: Hello world.
  • get_snippet: Retrieve a snippet by name.

# hello_mcp succeeds
✅ hello_mcp executed successfully

# save_snippet is denied
✅ Access control working: save_snippet correctly denied
   Response: {
     "jsonrpc": "2.0",
     "id": "test-tools/call-1",
     "error": {
       "code": -32001,
       "message": "Access denied: Tool 'save_snippet' is not available for your role(s): [\"reader\"]"
     }
   }
```

## Troubleshooting

### Issue: All users see all tools

**Cause**: Roles not properly configured in Entra ID token

**Solution**:
1. Verify app roles exist in App Registration
2. Confirm users are assigned to roles
3. Check token configuration includes `roles` claim
4. Inspect the JWT token to confirm roles are present

### Issue: 403 Forbidden for all tools

**Cause**: No roles found in token, user defaults to `user` role

**Solution**:
1. Assign user to appropriate role in Enterprise Applications
2. Ensure `roles` or `groups` claim is configured
3. Check role names match exactly (case-sensitive)

### Issue: Group memberships not working

**Cause**: Group GUIDs not mapped to role names in policy

**Solution**:
1. Get group GUIDs from Entra ID
2. Add mappings in roleToolMapping
3. Redeploy the APIM policy

## Performance Considerations

- **Caching**: Entra ID tokens are cached, role extraction happens once per session
- **Minimal overhead**: Role validation is in-memory comparison
- **Scalability**: APIM handles high throughput with horizontal scaling

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [Azure APIM Policies](https://learn.microsoft.com/en-us/azure/api-management/api-management-howto-policies)
- [Entra ID App Roles](https://learn.microsoft.com/en-us/azure/active-directory/develop/howto-add-app-roles-in-azure-ad-apps)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
