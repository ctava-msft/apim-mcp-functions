#!/usr/bin/env python3
"""
Simple MCP Endpoint Tester - Bypasses OAuth2 for direct testing
"""

import requests
import json

# Configuration
BASE_URL = "https://apim-hvsvkzkl6s2ra.azure-api.net"
MCP_SSE_URL = f"{BASE_URL}/mcp/sse"
MCP_MESSAGE_URL = f"{BASE_URL}/mcp/message"

def test_mcp_direct():
    """Test MCP endpoints directly without OAuth2"""
    print("🧪 Testing MCP Endpoints Directly")
    
    # Test 1: MCP SSE endpoint (should return 401 without auth)
    print("\n1. Testing MCP SSE endpoint (expected 401)...")
    try:
        response = requests.get(
            MCP_SSE_URL,
            headers={
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            },
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: MCP Message endpoint (should return 401 without auth)
    print("\n2. Testing MCP Message endpoint (expected 401)...")
    try:
        mcp_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        })
        
        response = requests.post(
            MCP_MESSAGE_URL,
            headers={"Content-Type": "application/json"},
            data=mcp_request,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Test with a mock Bearer token (should fail gracefully)
    print("\n3. Testing with mock Bearer token...")
    try:
        response = requests.get(
            MCP_SSE_URL,
            headers={
                "Authorization": "Bearer mock-token-12345",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            },
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Test MCP message endpoint with mock token
    print("\n4. Testing MCP Message endpoint with mock Bearer token...")
    try:
        mcp_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        })
        
        response = requests.post(
            MCP_MESSAGE_URL,
            headers={
                "Authorization": "Bearer mock-token-12345",
                "Content-Type": "application/json"
            },
            data=mcp_request,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")

def test_oauth_endpoints():
    """Test OAuth2 endpoints for availability"""
    print("\n🔐 Testing OAuth2 Endpoints")
    
    # Test register endpoint (POST)
    print(f"\n   Testing Client Registration: /register")
    try:
        response = requests.post(
            f"{BASE_URL}/register", 
            json={"redirect_uris": ["https://localhost"]},
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Registration successful!")
            reg_data = response.json()
            print(f"   Client ID: {reg_data.get('client_id', 'N/A')}")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test authorize endpoint (GET with params)
    print(f"\n   Testing Authorization: /authorize")
    try:
        params = {
            "response_type": "code",
            "client_id": "test",
            "redirect_uri": "https://localhost",
            "code_challenge": "test",
            "code_challenge_method": "S256",
            "state": "test"
        }
        response = requests.get(f"{BASE_URL}/authorize", params=params, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 302:
            print(f"   ✅ Redirects to: {response.headers.get('Location', 'N/A')}")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test token endpoint (POST)
    print(f"\n   Testing Token Exchange: /token")
    try:
        data = {
            "grant_type": "authorization_code",
            "code": "test",
            "code_verifier": "test"
        }
        response = requests.post(
            f"{BASE_URL}/token", 
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test other endpoints with GET
    other_endpoints = [
        ("/oauth-callback", "OAuth Callback"),
        ("/.well-known/oauth_authorization_server", "OAuth Metadata")
    ]
    
    for endpoint, name in other_endpoints:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n   Testing {name}: {endpoint}")
        try:
            response = requests.get(url, timeout=5)
            print(f"   Status: {response.status_code}")
            if response.status_code != 200:
                print(f"   Response: {response.text[:100]}...")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    print("🔧 Simple MCP & OAuth2 Endpoint Tester")
    print("=" * 50)
    
    test_oauth_endpoints()
    test_mcp_direct()
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")
    print("\nNext steps to fix OAuth2 500 error:")
    print("1. Check APIM named values are configured correctly")
    print("2. Verify Entra ID app registration is complete")
    print("3. Check that managed identity has proper permissions")
    print("4. Review APIM logs in Azure portal for detailed error information")