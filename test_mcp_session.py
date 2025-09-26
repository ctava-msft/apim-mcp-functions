#!/usr/bin/env python3
"""
MCP Session Test - Establish proper MCP session and test tools/list
"""

import requests
import json
import re

BASE_URL = "https://apim-hvsvkzkl6s2ra.azure-api.net"
ACCESS_TOKEN = "mcp_access_token_74f00413-f3a6-4354-a064-5d971d5c5138_mock_auth_code_123_1758909366"

def establish_mcp_session():
    """Establish MCP session and get tools list"""
    
    print("🔧 Testing MCP Server Session Establishment")
    print("=" * 50)
    
    # First, call the message endpoint to get session info
    print("\n1. Getting session endpoint...")
    try:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Try calling message endpoint to get session URL
        response = requests.post(
            f"{BASE_URL}/mcp/message",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        # Check if we got a session endpoint in the response
        if "message?" in response.text:
            # Extract the endpoint URL from the response
            match = re.search(r'message\?([^"]+)', response.text)
            if match:
                session_params = match.group(1)
                session_url = f"{BASE_URL}/mcp/message?{session_params}"
                print(f"   📍 Found session URL: {session_url}")
                
                # Now try to call the session-specific endpoint
                print("\n2. Testing with session URL...")
                session_response = requests.post(
                    session_url,
                    headers=headers,
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                    timeout=10
                )
                
                print(f"   Session Status: {session_response.status_code}")
                print(f"   Session Response: {session_response.text}")
                
                if session_response.status_code == 200:
                    try:
                        json_response = session_response.json()
                        print("   ✅ JSON Response:")
                        print(f"     {json.dumps(json_response, indent=2)}")
                        
                        # Check for hello_mcp tool
                        if "result" in json_response and "tools" in json_response["result"]:
                            tools = json_response["result"]["tools"]
                            hello_mcp_found = any(tool.get("name") == "hello_mcp" for tool in tools)
                            if hello_mcp_found:
                                print("   🎉 SUCCESS: hello_mcp tool found!")
                                return True
                            else:
                                print(f"   Available tools: {[tool.get('name') for tool in tools]}")
                        
                    except json.JSONDecodeError:
                        print("   Not JSON response")
                
    except Exception as e:
        print(f"   Error: {e}")
    
    # Alternative: Try direct backend call
    print("\n3. Testing direct backend call...")
    try:
        # Try calling the Azure Function directly
        backend_url = "https://func-api-h7gcxyzgb3hc6.azurewebsites.net/runtime/webhooks/mcp/message"
        
        # Get function key from APIM (this won't work without proper access, but let's try)
        direct_headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            backend_url,
            headers=direct_headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            timeout=10
        )
        
        print(f"   Direct Status: {response.status_code}")
        print(f"   Direct Response: {response.text[:500]}...")
        
    except Exception as e:
        print(f"   Direct Error: {e}")
    
    return False

if __name__ == "__main__":
    establish_mcp_session()