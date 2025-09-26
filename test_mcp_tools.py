#!/usr/bin/env python3
"""
Direct MCP Client Test - Test MCP Server tools/list call
"""

import requests
import json

BASE_URL = "https://apim-hvsvkzkl6s2ra.azure-api.net"
ACCESS_TOKEN = "mcp_access_token_74f00413-f3a6-4354-a064-5d971d5c5138_mock_auth_code_123_1758909366"

def test_mcp_tools_list():
    """Test the MCP server's tools/list endpoint to see if hello_mcp tool is returned"""
    
    print("🔧 Testing MCP Server - tools/list")
    print("=" * 50)
    
    # First, let's try to establish a session with the SSE endpoint
    print("\n1. Testing SSE endpoint connection...")
    try:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }
        
        response = requests.get(
            f"{BASE_URL}/mcp/sse",
            headers=headers,
            timeout=5,
            stream=True
        )
        
        print(f"   SSE Status: {response.status_code}")
        if response.status_code == 200:
            # Read first few lines of the SSE stream
            lines = []
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    lines.append(line)
                    if len(lines) >= 5:  # Read first 5 lines
                        break
            
            print("   SSE Response (first 5 lines):")
            for line in lines:
                print(f"     {line}")
        else:
            print(f"   SSE Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   SSE Error: {e}")
    
    # Now test the message endpoint with tools/list
    print("\n2. Testing tools/list request...")
    try:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Standard MCP JSON-RPC request for tools/list
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        
        response = requests.post(
            f"{BASE_URL}/mcp/message",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                json_response = response.json()
                print("   ✅ JSON Response:")
                print(f"     {json.dumps(json_response, indent=2)}")
                
                # Check if hello_mcp tool is in the response
                if "result" in json_response and "tools" in json_response["result"]:
                    tools = json_response["result"]["tools"]
                    hello_mcp_found = any(tool.get("name") == "hello_mcp" for tool in tools)
                    if hello_mcp_found:
                        print("   🎉 SUCCESS: hello_mcp tool found in tools list!")
                    else:
                        print("   ⚠️  hello_mcp tool not found in tools list")
                        print(f"   Available tools: {[tool.get('name') for tool in tools]}")
                else:
                    print("   ⚠️  No tools found in response")
                    
            except json.JSONDecodeError:
                print("   Response (not JSON):")
                print(f"     {response.text}")
        else:
            print(f"   Error Response: {response.text}")
            
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_mcp_tools_list()