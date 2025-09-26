#!/usr/bin/env python3
"""
Enhanced MCP Server Tester with OAuth2 Authentication
=====================================================

This script tests the MCP server endpoints and implements the OAuth2 PKCE flow
for authentication. It can register as an OAuth2 client, perform the authorization
flow, and use the acquired tokens to test MCP endpoints.

Usage Examples:
===============

# Interactive mode (will prompt for choice)
python test_mcp_server.py

# Basic connectivity test (no authentication)
python test_mcp_server.py 1

# Generate OAuth2 authorization URL
python test_mcp_server.py url

# Exchange authorization code for token and test MCP endpoints
python test_mcp_server.py code AUTHORIZATION_CODE_HERE

# Test with existing saved tokens
python test_mcp_server.py 4

OAuth2 Flow:
============
1. Run: python test_mcp_server.py url
2. Copy the authorization URL and open in browser
3. Complete OAuth2 login flow
4. Copy the 'code' parameter from the callback URL
5. Run: python test_mcp_server.py code <YOUR_CODE>

The script automatically saves and reuses tokens in 'mcp_tokens.json'.
"""

import requests
import json
import sys
import base64
import hashlib
import secrets
import urllib.parse
import webbrowser
import time
from typing import Dict, Any, Optional, Tuple
import os

# Configuration
BASE_URL = "https://apim-hvsvkzkl6s2ra.azure-api.net"
MCP_SSE_URL = f"{BASE_URL}/mcp/sse"
MCP_MESSAGE_URL = f"{BASE_URL}/mcp/message"

# OAuth2 configuration
OAUTH_REGISTER_URL = f"{BASE_URL}/register"
OAUTH_AUTHORIZE_URL = f"{BASE_URL}/authorize"
OAUTH_TOKEN_URL = f"{BASE_URL}/token"
OAUTH_CALLBACK_URL = f"{BASE_URL}/oauth-callback"

# Token storage
TOKEN_FILE = "mcp_tokens.json"

class OAuth2Client:
    """OAuth2 client with PKCE support for MCP server authentication."""
    
    def __init__(self):
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.access_token: Optional[str] = None
        self.encrypted_session_key: Optional[str] = None
        self.code_verifier: Optional[str] = None
        self.code_challenge: Optional[str] = None
        self.state: Optional[str] = None
        
        # Load existing tokens if available
        self.load_tokens()
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        # Generate random code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def register_client(self) -> bool:
        """Register as OAuth2 client with the MCP server."""
        print("\n🔐 Registering OAuth2 client...")
        
        registration_data = {
            "client_name": "MCP Test Client (Python)",
            "client_uri": "http://localhost:8000",
            "redirect_uris": [OAUTH_CALLBACK_URL],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "application_type": "native"
        }
        
        try:
            response = requests.post(
                OAUTH_REGISTER_URL,
                headers={"Content-Type": "application/json"},
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                client_info = response.json()
                self.client_id = client_info.get("client_id")
                self.client_secret = client_info.get("client_secret")
                
                print(f"✅ Client registered successfully!")
                print(f"   Client ID: {self.client_id}")
                print(f"   Client Secret: {'***' if self.client_secret else 'None'}")
                
                self.save_tokens()
                return True
            else:
                print(f"❌ Registration failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def start_authorization_flow(self) -> str:
        """Start OAuth2 authorization flow with PKCE."""
        if not self.client_id:
            print("❌ No client ID available. Register client first.")
            return ""
        
        print("\n🔑 Starting OAuth2 authorization flow...")
        
        # Generate PKCE parameters
        self.code_verifier, self.code_challenge = self.generate_pkce_pair()
        self.state = secrets.token_urlsafe(32)
        
        # Save PKCE parameters for later use
        self.save_tokens()
        
        # Build authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": OAUTH_CALLBACK_URL,
            "scope": "openid https://graph.microsoft.com/.default",
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256"
        }
        
        auth_url = f"{OAUTH_AUTHORIZE_URL}?" + urllib.parse.urlencode(auth_params)
        
        print(f"🌐 Authorization URL: {auth_url}")
        print("\n📋 Manual Steps Required:")
        print("1. Copy the URL above and open it in your browser")
        print("2. Complete the OAuth2 authorization flow")
        print("3. After callback, copy the 'code' parameter from the URL")
        print("4. Enter the code when prompted below")
        
        return auth_url
    
    def exchange_code_for_token(self, auth_code: str) -> bool:
        """Exchange authorization code for access token."""
        if not self.client_id or not self.code_verifier:
            print("❌ Missing client ID or code verifier")
            return False
        
        print(f"\n🔄 Exchanging authorization code for token...")
        
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": OAUTH_CALLBACK_URL,
            "client_id": self.client_id,
            "code_verifier": self.code_verifier
        }
        
        try:
            response = requests.post(
                OAUTH_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=token_data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_info = response.json()
                
                # The MCP server returns an encrypted session key
                self.encrypted_session_key = token_info.get("access_token")
                self.access_token = token_info.get("access_token")  # Same value
                
                print("✅ Token exchange successful!")
                print(f"   Encrypted Session Key: {self.encrypted_session_key[:20]}...")
                
                self.save_tokens()
                return True
            else:
                print(f"❌ Token exchange failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Token exchange error: {e}")
            return False
    
    def save_tokens(self):
        """Save tokens to file."""
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "access_token": self.access_token,
            "encrypted_session_key": self.encrypted_session_key,
            "code_verifier": self.code_verifier,
            "code_challenge": self.code_challenge,
            "state": self.state
        }
        
        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(token_data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save tokens: {e}")
    
    def load_tokens(self):
        """Load tokens from file."""
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                
                self.client_id = token_data.get("client_id")
                self.client_secret = token_data.get("client_secret")
                self.access_token = token_data.get("access_token")
                self.encrypted_session_key = token_data.get("encrypted_session_key")
                self.code_verifier = token_data.get("code_verifier")
                self.code_challenge = token_data.get("code_challenge")
                self.state = token_data.get("state")
                
                if self.access_token:
                    print(f"📁 Loaded existing tokens from {TOKEN_FILE}")
                    # If we have access_token but no encrypted_session_key, use access_token
                    if not self.encrypted_session_key:
                        self.encrypted_session_key = self.access_token
        except Exception as e:
            print(f"⚠️  Could not load tokens: {e}")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        if not self.encrypted_session_key:
            return {}
        
        return {
            "Authorization": f"Bearer {self.encrypted_session_key}"
        }

def test_endpoint(url: str, method: str = "GET", headers: Dict[str, str] = None, 
                 data: str = None, description: str = "") -> Dict[str, Any]:
    """Test an endpoint and return the results."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print(f"Method: {method}")
    
    if headers:
        # Hide authorization token in logs for security
        display_headers = dict(headers)
        if "Authorization" in display_headers:
            auth_value = display_headers["Authorization"]
            if auth_value.startswith("Bearer "):
                display_headers["Authorization"] = f"Bearer {auth_value[7:15]}..."
        print(f"Headers: {json.dumps(display_headers, indent=2)}")
    
    if data:
        print(f"Data: {data}")
    
    result = {"success": False, "status_code": None, "response": None}
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, data=data, timeout=10)
        else:
            print(f"Unsupported method: {method}")
            return result
            
        result["status_code"] = response.status_code
        result["success"] = response.status_code < 400
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        # Try to format JSON response
        try:
            json_response = response.json()
            result["response"] = json_response
            print(f"Response Body: {json.dumps(json_response, indent=2)}")
        except:
            result["response"] = response.text
            print(f"Response Body: {response.text}")
            
        return result
            
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        result["response"] = str(e)
        return result

def test_oauth_endpoints(oauth_client: OAuth2Client):
    """Test OAuth2 related endpoints."""
    print("🔐 Testing OAuth2 Endpoints")
    
    # Test OAuth metadata endpoint
    test_endpoint(
        f"{BASE_URL}/.well-known/oauth_authorization_server",
        "GET",
        description="OAuth2 Metadata Discovery"
    )
    
    # Test client registration (if not already done)
    if not oauth_client.client_id:
        if not oauth_client.register_client():
            print("❌ Failed to register OAuth2 client")
            return False
    else:
        print(f"✅ Using existing client ID: {oauth_client.client_id}")
    
    return True

def test_mcp_endpoints_unauthenticated():
    """Test MCP endpoints without authentication (should return 401)."""
    print("\n🔌 Testing MCP Endpoints (Expected 401 responses)")
    
    # Test SSE endpoint
    test_endpoint(
        MCP_SSE_URL,
        "GET",
        headers={
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        },
        description="MCP SSE Endpoint (no auth)"
    )
    
    # Test message endpoint with tools/list
    mcp_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    })
    
    test_endpoint(
        MCP_MESSAGE_URL,
        "POST",
        headers={"Content-Type": "application/json"},
        data=mcp_request,
        description="MCP Tools List (no auth)"
    )

def test_mcp_endpoints_authenticated(oauth_client: OAuth2Client):
    """Test MCP endpoints with authentication."""
    if not oauth_client.encrypted_session_key:
        print("\n❌ No authentication token available")
        return False
    
    print("\n🔌 Testing MCP Endpoints (With Authentication)")
    
    auth_headers = oauth_client.get_auth_headers()
    
    # Test SSE endpoint
    sse_result = test_endpoint(
        MCP_SSE_URL,
        "GET",
        headers={
            **auth_headers,
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        },
        description="MCP SSE Endpoint (authenticated)"
    )
    
    # Test message endpoint with tools/list
    mcp_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    })
    
    tools_result = test_endpoint(
        MCP_MESSAGE_URL,
        "POST",
        headers={
            **auth_headers,
            "Content-Type": "application/json"
        },
        data=mcp_request,
        description="MCP Tools List (authenticated)"
    )
    
    # If tools/list worked, try calling hello_mcp
    if tools_result.get("success"):
        mcp_hello_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "hello_mcp",
                "arguments": {}
            }
        })
        
        test_endpoint(
            MCP_MESSAGE_URL,
            "POST",
            headers={
                **auth_headers,
                "Content-Type": "application/json"
            },
            data=mcp_hello_request,
            description="MCP Hello Tool (authenticated)"
        )
        
        # Try save_snippet tool
        mcp_save_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "save_snippet",
                "arguments": {
                    "snippetname": "test-snippet-" + str(int(time.time())),
                    "snippet": "This is a test snippet from the Python OAuth2 client"
                }
            }
        })
        
        save_result = test_endpoint(
            MCP_MESSAGE_URL,
            "POST",
            headers={
                **auth_headers,
                "Content-Type": "application/json"
            },
            data=mcp_save_request,
            description="MCP Save Snippet Tool (authenticated)"
        )
        
        # If save worked, try to retrieve it
        if save_result.get("success"):
            snippet_name = json.loads(mcp_save_request)["params"]["arguments"]["snippetname"]
            
            mcp_get_request = json.dumps({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "get_snippet",
                    "arguments": {
                        "snippetname": snippet_name
                    }
                }
            })
            
            test_endpoint(
                MCP_MESSAGE_URL,
                "POST",
                headers={
                    **auth_headers,
                    "Content-Type": "application/json"
                },
                data=mcp_get_request,
                description="MCP Get Snippet Tool (authenticated)"
            )
    
    return True

def interactive_oauth_flow(oauth_client: OAuth2Client) -> bool:
    """Run interactive OAuth2 flow."""
    print("\n🔐 Starting Interactive OAuth2 Flow")
    
    if not oauth_client.client_id:
        print("❌ No client registered. Please register first.")
        return False
    
    # Start authorization flow
    auth_url = oauth_client.start_authorization_flow()
    
    if not auth_url:
        return False
    
    # Wait for user to complete flow
    print(f"\n⏳ Waiting for you to complete the OAuth2 flow...")
    
    # Prompt for authorization code
    try:
        # Check if stdin is available for interactive input
        if not sys.stdin.isatty() and not sys.stdin.readable():
            print("❌ Cannot read authorization code in non-interactive mode")
            print("💡 Run the script interactively to complete OAuth2 flow")
            return False
        
        auth_code = input("\n📝 Enter the authorization code from the callback URL: ").strip()
        
        if not auth_code:
            print("❌ No authorization code provided")
            return False
        
        # Exchange code for token
        return oauth_client.exchange_code_for_token(auth_code)
        
    except (KeyboardInterrupt, EOFError):
        print("\n❌ OAuth2 flow cancelled or input unavailable")
        print("💡 To complete OAuth2 flow:")
        print("   1. Run: python test_mcp_server.py")
        print("   2. Choose option 3")
        print("   3. Enter the authorization code when prompted")
        return False

def main():
    """Main test function."""
    print("🧪 Enhanced MCP Server Test Suite with OAuth2")
    print(f"Testing server: {BASE_URL}")
    print("\nThis script can:")
    print("1. Test basic endpoint connectivity")
    print("2. Register as OAuth2 client")
    print("3. Perform interactive OAuth2 authentication")
    print("4. Test MCP endpoints with authentication")
    print()
    
    # Initialize OAuth2 client
    oauth_client = OAuth2Client()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        choice = sys.argv[1]
        print(f"📋 Running with command line option: {choice}")
    else:
        choice = None
    
    try:
        # Ask user what they want to do
        print("Select test mode:")
        print("1. Basic connectivity test (no auth)")
        print("2. OAuth2 client registration only")
        print("3. Full OAuth2 flow and MCP testing (interactive)")
        print("4. Test with existing tokens")
        print("5. Generate OAuth2 URL only (non-interactive)")
        print("\nCommand line usage:")
        print("  python test_mcp_server.py 1    # Basic test")
        print("  python test_mcp_server.py url  # Generate OAuth URL")
        print("  python test_mcp_server.py code <AUTH_CODE>  # Exchange code")
        
        if choice is None:
            try:
                choice = input("\nEnter choice (1-4): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n❌ Input cancelled or unavailable")
                print("💡 Running basic connectivity test (option 1) by default...")
                choice = "1"
        
        if choice == "1":
            # Basic connectivity test
            print("\n🔍 Running basic connectivity tests...")
            test_oauth_endpoints(oauth_client)
            test_mcp_endpoints_unauthenticated()
            
        elif choice == "2":
            # OAuth2 registration only
            print("\n🔐 Running OAuth2 client registration...")
            if test_oauth_endpoints(oauth_client):
                print("✅ OAuth2 client registration completed")
            else:
                print("❌ OAuth2 client registration failed")
                
        elif choice == "3":
            # Full OAuth2 flow
            print("\n🚀 Running full OAuth2 flow and MCP testing...")
            
            # Register client if needed
            if not test_oauth_endpoints(oauth_client):
                print("❌ OAuth2 setup failed")
                return
            
            # Run interactive OAuth2 flow
            if interactive_oauth_flow(oauth_client):
                print("✅ OAuth2 authentication successful!")
                
                # Test MCP endpoints with authentication
                test_mcp_endpoints_authenticated(oauth_client)
            else:
                print("❌ OAuth2 authentication failed")
                
        elif choice == "url" or choice == "5":
            # Generate OAuth URL only
            print("\n🔗 Generating OAuth2 authorization URL...")
            
            # Register client if needed
            if not test_oauth_endpoints(oauth_client):
                print("❌ OAuth2 setup failed")
                return
            
            # Generate authorization URL
            auth_url = oauth_client.start_authorization_flow()
            
            if auth_url:
                print(f"\n🌐 Copy this URL and open it in your browser:")
                print(f"{auth_url}")
                print(f"\n📝 After completing OAuth2 flow, run:")
                print(f"   python test_mcp_server.py code <AUTHORIZATION_CODE>")
            else:
                print("❌ Failed to generate authorization URL")
                
        elif choice == "code" and len(sys.argv) > 2:
            # Exchange authorization code for token
            auth_code = sys.argv[2]
            print(f"\n🔄 Exchanging authorization code for token...")
            
            if oauth_client.exchange_code_for_token(auth_code):
                print("✅ OAuth2 authentication successful!")
                
                # Test MCP endpoints with authentication
                test_mcp_endpoints_authenticated(oauth_client)
            else:
                print("❌ OAuth2 authentication failed")
                
        elif choice == "4":
            # Test with existing tokens
            print("\n🔑 Testing with existing tokens...")
            
            if oauth_client.encrypted_session_key:
                print(f"✅ Found existing token: {oauth_client.encrypted_session_key[:20]}...")
                test_mcp_endpoints_authenticated(oauth_client)
            else:
                print("❌ No existing tokens found")
                print("Run option 3 to complete OAuth2 flow first")
                
        else:
            print("❌ Invalid choice")
            return
        
        print(f"\n{'='*60}")
        print("🎯 Test Summary:")
        print("- 401 responses from /mcp/* endpoints without auth = ✅ Security working")
        print("- 200 responses from OAuth2 endpoints = ✅ OAuth flow available")
        print("- 200 responses from /mcp/* endpoints with auth = ✅ Authentication working")
        print("- Network errors = ❌ Check if deployment is accessible")
        
        print(f"\n💾 Token Storage:")
        print(f"- Tokens saved to: {TOKEN_FILE}")
        print(f"- Rerun with option 4 to use saved tokens")
        
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()