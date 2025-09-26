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
        self.sse_task = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.sse_task:
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass
        if self.session:
            await self.session.close()
    
    async def maintain_sse_connection(self):
        """Maintain SSE connection in background"""
        try:
            print(f"🔗 Establishing persistent SSE connection...")
            async with self.session.get(f'{self.base_url}/sse') as response:
                print(f"📡 SSE Status: {response.status}")
                if response.status == 200:
                    print(f"✅ SSE connection established, reading stream...")
                    async for line in response.content:
                        if line:
                            decoded = line.decode('utf-8', errors='ignore').strip()
                            if decoded:
                                print(f"📡 SSE: {decoded}")
                else:
                    print(f"❌ SSE connection failed with status {response.status}")
        except Exception as e:
            print(f"❌ SSE connection error: {e}")
    
    async def send_jsonrpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request to the message endpoint"""
        request_id = str(uuid.uuid4())
        
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

async def test_mcp_concurrent_session():
    """Test MCP with concurrent SSE connection and JSON-RPC requests"""
    
    # Load OAuth token
    try:
        with open('mcp_tokens.json', 'r') as f:
            tokens = json.load(f)
            access_token = tokens['access_token']
    except Exception as e:
        print(f"❌ Could not load access token: {e}")
        return False
    
    base_url = 'https://apim-hvsvkzkl6s2ra.azure-api.net/mcp'
    
    print(f"🚀 Starting Concurrent MCP Session Test")
    print(f"🔗 Base URL: {base_url}")
    print(f"🎫 Access Token: {access_token[:20]}...")
    
    async with MCPSessionManager(base_url, access_token) as mcp:
        # Start SSE connection in background
        print(f"\n📡 Starting SSE connection in background...")
        mcp.sse_task = asyncio.create_task(mcp.maintain_sse_connection())
        
        # Give SSE connection time to establish
        await asyncio.sleep(2)
        
        # Send tools/list request
        print(f"\n🛠️  Sending tools/list request...")
        tools_response = await mcp.send_jsonrpc_request("tools/list")
        print(f"🛠️  Tools Response: {json.dumps(tools_response, indent=2)}")
        
        # Check if hello_mcp tool is present
        print(f"\n🔍 Analyzing Response...")
        
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
        result = asyncio.run(test_mcp_concurrent_session())
        if result:
            print(f"\n🎉 SUCCESS: hello_mcp tool found and working!")
            sys.exit(0)
        else:
            print(f"\n💥 FAILED: Could not find hello_mcp tool")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        sys.exit(1)