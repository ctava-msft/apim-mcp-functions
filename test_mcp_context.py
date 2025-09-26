#!/usr/bin/env python3

import asyncio
import json
import aiohttp
import sys
from typing import Dict, Any, Optional
import uuid

class MCPSessionManager:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session = None
        self.session_cookies = None
        
    async def __aenter__(self):
        # Create session with cookie jar to maintain session state
        jar = aiohttp.CookieJar()
        self.session = aiohttp.ClientSession(
            cookie_jar=jar,
            headers={
                'Authorization': f'Bearer {self.auth_token}',
                'User-Agent': 'MCP-Test-Client/1.0'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def establish_session_context(self):
        """Establish session context by connecting to SSE and extracting session info"""
        try:
            print(f"🔗 Connecting to SSE endpoint to establish session context...")
            
            async with self.session.get(f'{self.base_url}/sse') as response:
                print(f"📡 SSE Response Status: {response.status}")
                print(f"📡 SSE Response Headers: {dict(response.headers)}")
                
                # Check for cookies
                if hasattr(response, 'cookies') and response.cookies:
                    print(f"🍪 Response Cookies: {dict(response.cookies)}")
                
                if response.status == 200:
                    # Try to read initial SSE data for session establishment
                    try:
                        content_reader = response.content
                        # Read first few chunks with timeout
                        for i in range(5):  # Try to read up to 5 chunks
                            try:
                                chunk = await asyncio.wait_for(content_reader.read(1024), timeout=1.0)
                                if chunk:
                                    decoded = chunk.decode('utf-8', errors='ignore')
                                    print(f"📡 SSE Chunk {i+1}: {decoded}")
                                    # Look for session info in SSE data
                                    if 'session' in decoded.lower() or 'id' in decoded.lower():
                                        print(f"✅ Potential session info found!")
                                else:
                                    break
                            except asyncio.TimeoutError:
                                print(f"⏰ Timeout reading SSE chunk {i+1}")
                                break
                    except Exception as e:
                        print(f"📡 SSE read error: {e}")
                    
                    return True
                else:
                    print(f"❌ SSE connection failed with status {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ SSE connection error: {e}")
            return False
    
    async def send_jsonrpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request to the message endpoint using the same session"""
        request_id = str(uuid.uuid4())
        
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        
        if params:
            jsonrpc_request["params"] = params
            
        print(f"📤 Sending JSON-RPC request: {json.dumps(jsonrpc_request, indent=2)}")
        
        # Use the same session that was used for SSE
        try:
            async with self.session.post(
                f'{self.base_url}/message',
                json=jsonrpc_request,
                headers={'Content-Type': 'application/json'}
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

async def test_mcp_session_context():
    """Test MCP with proper session context management"""
    
    # Load OAuth token
    try:
        with open('mcp_tokens.json', 'r') as f:
            tokens = json.load(f)
            access_token = tokens['access_token']
    except Exception as e:
        print(f"❌ Could not load access token: {e}")
        return False
    
    base_url = 'https://apim-hvsvkzkl6s2ra.azure-api.net/mcp'
    
    print(f"🚀 Starting MCP Session Context Test")
    print(f"🔗 Base URL: {base_url}")
    print(f"🎫 Access Token: {access_token[:20]}...")
    
    async with MCPSessionManager(base_url, access_token) as mcp:
        # Step 1: Establish session context via SSE
        print(f"\n" + "="*50)
        print(f"📡 STEP 1: Establishing Session Context")
        print("="*50)
        
        session_established = await mcp.establish_session_context()
        if not session_established:
            print(f"❌ Failed to establish session context")
            return False
        
        print(f"✅ Session context established")
        
        # Step 2: Send tools/list request using same session
        print(f"\n" + "="*50)
        print(f"🛠️  STEP 2: Sending tools/list Request")
        print("="*50)
        
        tools_response = await mcp.send_jsonrpc_request("tools/list")
        print(f"🛠️  Tools Response: {json.dumps(tools_response, indent=2)}")
        
        # Step 3: Check if hello_mcp tool is present
        print(f"\n" + "="*50)
        print(f"🔍 STEP 3: Analyzing Response")
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
        result = asyncio.run(test_mcp_session_context())
        if result:
            print(f"\n🎉 SUCCESS: hello_mcp tool found and working!")
            sys.exit(0)
        else:
            print(f"\n💥 FAILED: Could not find hello_mcp tool")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        sys.exit(1)