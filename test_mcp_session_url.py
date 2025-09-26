#!/usr/bin/env python3

import asyncio
import json
import aiohttp
import sys
from typing import Dict, Any, Optional
import uuid
import re
from urllib.parse import parse_qs, urlparse

class MCPSessionManager:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session = None
        self.session_message_url = None
        
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
    
    def parse_sse_event(self, sse_data: str) -> Optional[str]:
        """Parse SSE data to extract message endpoint URL"""
        lines = sse_data.strip().split('\n')
        event_type = None
        data_content = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('event:'):
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                data_content = line[5:].strip()
        
        if event_type == 'endpoint' and data_content:
            # The data contains the session-specific message endpoint
            return data_content
        
        return None
    
    async def establish_session_context(self):
        """Establish session context by connecting to SSE and extracting session URL"""
        try:
            print(f"🔗 Connecting to SSE endpoint to establish session context...")
            
            async with self.session.get(f'{self.base_url}/sse') as response:
                print(f"📡 SSE Response Status: {response.status}")
                
                if response.status == 200:
                    # Read SSE data to get session endpoint
                    try:
                        content_reader = response.content
                        # Read first chunk which should contain the endpoint info
                        chunk = await asyncio.wait_for(content_reader.read(2048), timeout=3.0)
                        if chunk:
                            decoded = chunk.decode('utf-8', errors='ignore')
                            print(f"📡 SSE Data: {decoded}")
                            
                            # Parse the SSE event
                            session_endpoint = self.parse_sse_event(decoded)
                            if session_endpoint:
                                # Construct full URL - endpoint data is relative to base
                                if session_endpoint.startswith('message?'):
                                    self.session_message_url = f"{self.base_url}/{session_endpoint}"
                                else:
                                    self.session_message_url = f"{self.base_url}/message?{session_endpoint}"
                                
                                print(f"✅ Session Message URL: {self.session_message_url}")
                                return True
                            else:
                                print(f"❌ Could not parse session endpoint from SSE data")
                                return False
                        else:
                            print(f"❌ No SSE data received")
                            return False
                            
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout reading SSE data")
                        return False
                    except Exception as e:
                        print(f"📡 SSE read error: {e}")
                        return False
                else:
                    print(f"❌ SSE connection failed with status {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ SSE connection error: {e}")
            return False
    
    async def send_jsonrpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request to the session-specific message endpoint"""
        if not self.session_message_url:
            return {"error": "No session context established"}
        
        request_id = str(uuid.uuid4())
        
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        
        if params:
            jsonrpc_request["params"] = params
            
        print(f"📤 Sending JSON-RPC request to session URL: {self.session_message_url}")
        print(f"📤 Request: {json.dumps(jsonrpc_request, indent=2)}")
        
        try:
            async with self.session.post(
                self.session_message_url,
                json=jsonrpc_request,
                headers={'Content-Type': 'application/json'}
            ) as response:
                print(f"📨 Message Response Status: {response.status}")
                
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

async def test_mcp_session_url():
    """Test MCP with session-specific URL extraction"""
    
    # Load OAuth token
    try:
        with open('mcp_tokens.json', 'r') as f:
            tokens = json.load(f)
            access_token = tokens['access_token']
    except Exception as e:
        print(f"❌ Could not load access token: {e}")
        return False
    
    base_url = 'https://apim-hvsvkzkl6s2ra.azure-api.net/mcp'
    
    print(f"🚀 Starting MCP Session URL Test")
    print(f"🔗 Base URL: {base_url}")
    print(f"🎫 Access Token: {access_token[:20]}...")
    
    async with MCPSessionManager(base_url, access_token) as mcp:
        # Step 1: Establish session context and get session URL
        print(f"\n" + "="*60)
        print(f"📡 STEP 1: Establishing Session Context & Extracting URL")
        print("="*60)
        
        session_established = await mcp.establish_session_context()
        if not session_established:
            print(f"❌ Failed to establish session context")
            return False
        
        print(f"✅ Session context established with URL: {mcp.session_message_url}")
        
        # Step 2: Send tools/list request using session-specific URL
        print(f"\n" + "="*60)
        print(f"🛠️  STEP 2: Sending tools/list Request to Session URL")
        print("="*60)
        
        tools_response = await mcp.send_jsonrpc_request("tools/list")
        print(f"🛠️  Tools Response: {json.dumps(tools_response, indent=2)}")
        
        # Step 3: Check if hello_mcp tool is present
        print(f"\n" + "="*60)
        print(f"🔍 STEP 3: Analyzing Response for hello_mcp Tool")
        print("="*60)
        
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
                    print(f"    ✅ FOUND hello_mcp tool!")
                    
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
        result = asyncio.run(test_mcp_session_url())
        if result:
            print(f"\n🎉 SUCCESS: hello_mcp tool found and working!")
            print(f"🎉 The MCP server is properly returning the hello_mcp tool!")
            sys.exit(0)
        else:
            print(f"\n💥 FAILED: Could not find hello_mcp tool")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        sys.exit(1)