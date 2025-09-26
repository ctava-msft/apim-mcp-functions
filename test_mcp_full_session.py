#!/usr/bin/env python3

import asyncio
import json
import aiohttp
import sys
from typing import Dict, Any, Optional

class MCPSessionManager:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session_id = None
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def establish_sse_session(self) -> bool:
        """Try to establish an SSE connection to get session info"""
        try:
            print(f"🔗 Connecting to SSE endpoint: {self.base_url}/sse")
            
            async with self.session.get(f'{self.base_url}/sse') as response:
                print(f"📡 SSE Response Status: {response.status}")
                print(f"📡 SSE Response Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    # Try to read some initial data with timeout
                    try:
                        async with asyncio.timeout(5):  # 5 second timeout
                            content = await response.read()
                            if content:
                                print(f"📡 SSE Initial Content: {content.decode()[:200]}...")
                                # Try to extract session info if available
                                self.session_id = "sse_established"
                                return True
                    except asyncio.TimeoutError:
                        print("⏰ SSE connection timed out (expected for streaming)")
                        self.session_id = "sse_timeout"
                        return True
                        
        except Exception as e:
            print(f"❌ SSE connection error: {e}")
            return False
    
    async def send_jsonrpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request to the message endpoint"""
        request_id = "test-request-1"
        
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        
        if params:
            jsonrpc_request["params"] = params
            
        print(f"📤 Sending JSON-RPC request: {json.dumps(jsonrpc_request, indent=2)}")
        
        try:
            async with self.session.post(
                f'{self.base_url}/message',
                json=jsonrpc_request
            ) as response:
                print(f"📨 Message Response Status: {response.status}")
                print(f"📨 Message Response Headers: {dict(response.headers)}")
                
                response_text = await response.text()
                print(f"📨 Message Response Body: {response_text}")
                
                if response.status == 200:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        return {"error": "Invalid JSON response", "raw": response_text}
                else:
                    return {
                        "error": f"HTTP {response.status}",
                        "status": response.status,
                        "body": response_text
                    }
                    
        except Exception as e:
            return {"error": str(e)}

async def test_mcp_session():
    """Test MCP session establishment and tools/list request"""
    
    # Load OAuth token
    try:
        with open('mcp_tokens.json', 'r') as f:
            tokens = json.load(f)
            access_token = tokens['access_token']
    except Exception as e:
        print(f"❌ Could not load access token: {e}")
        return False
    
    base_url = 'https://apim-hvsvkzkl6s2ra.azure-api.net/mcp'
    
    print(f"🚀 Starting MCP Session Test")
    print(f"🔗 Base URL: {base_url}")
    print(f"🎫 Access Token: {access_token[:20]}...")
    
    async with MCPSessionManager(base_url, access_token) as mcp:
        # Step 1: Try to establish SSE session
        print("\n" + "="*50)
        print("📡 STEP 1: Establishing SSE Session")
        print("="*50)
        
        sse_success = await mcp.establish_sse_session()
        print(f"📡 SSE Session Result: {'✅ Success' if sse_success else '❌ Failed'}")
        
        # Step 2: Send tools/list request regardless of SSE status
        print("\n" + "="*50)
        print("🛠️  STEP 2: Sending tools/list Request")
        print("="*50)
        
        tools_response = await mcp.send_jsonrpc_request("tools/list")
        print(f"🛠️  Tools Response: {json.dumps(tools_response, indent=2)}")
        
        # Step 3: Check if hello_mcp tool is present
        print("\n" + "="*50)
        print("🔍 STEP 3: Analyzing Response")
        print("="*50)
        
        if "result" in tools_response and "tools" in tools_response["result"]:
            tools = tools_response["result"]["tools"]
            print(f"🛠️  Found {len(tools)} tools:")
            
            hello_mcp_found = False
            for tool in tools:
                tool_name = tool.get("name", "unknown")
                tool_desc = tool.get("description", "")
                print(f"  • {tool_name}: {tool_desc}")
                
                if tool_name == "hello_mcp":
                    hello_mcp_found = True
                    print(f"    ✅ Found hello_mcp tool!")
                    
            if not hello_mcp_found:
                print(f"    ❌ hello_mcp tool not found in response")
                
            return hello_mcp_found
            
        elif "error" in tools_response:
            print(f"❌ JSON-RPC Error: {tools_response['error']}")
            return False
        else:
            print(f"❌ Unexpected response format")
            return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_mcp_session())
        if result:
            print(f"\n🎉 SUCCESS: hello_mcp tool found and working!")
            sys.exit(0)
        else:
            print(f"\n💥 FAILED: Could not find hello_mcp tool")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        sys.exit(1)