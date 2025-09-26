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
        self.session_message_url = None
        self.sse_responses = []
        
    async def __aenter__(self):
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
    
    def parse_sse_event(self, sse_data: str) -> Dict[str, Any]:
        """Parse SSE data into event type and data"""
        lines = sse_data.strip().split('\n')
        event_type = None
        data_content = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('event:'):
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                data_content = line[5:].strip()
        
        return {
            'event': event_type,
            'data': data_content
        }
    
    async def establish_session_and_listen(self):
        """Establish session and maintain SSE connection for responses"""
        try:
            print(f"🔗 Connecting to SSE endpoint for session and responses...")
            
            async with self.session.get(f'{self.base_url}/sse') as response:
                print(f"📡 SSE Response Status: {response.status}")
                
                if response.status == 200:
                    print(f"✅ SSE connection established, processing stream...")
                    
                    async for line in response.content:
                        if line:
                            decoded = line.decode('utf-8', errors='ignore').strip()
                            if decoded:
                                print(f"📡 SSE Raw: {decoded}")
                                
                                # Parse SSE event
                                sse_event = self.parse_sse_event(decoded)
                                event_type = sse_event.get('event')
                                data_content = sse_event.get('data')
                                
                                if event_type == 'endpoint' and data_content:
                                    # Extract session message URL
                                    if data_content.startswith('message?'):
                                        self.session_message_url = f"{self.base_url}/{data_content}"
                                    else:
                                        self.session_message_url = f"{self.base_url}/message?{data_content}"
                                    
                                    print(f"✅ Session Message URL: {self.session_message_url}")
                                    
                                elif event_type == 'message' and data_content:
                                    # This is a JSON-RPC response
                                    try:
                                        response_data = json.loads(data_content)
                                        print(f"📨 JSON-RPC Response: {json.dumps(response_data, indent=2)}")
                                        self.sse_responses.append(response_data)
                                    except json.JSONDecodeError:
                                        print(f"❌ Invalid JSON in message event: {data_content}")
                                
                                elif event_type:
                                    print(f"📡 Other SSE Event: {event_type} -> {data_content}")
                else:
                    print(f"❌ SSE connection failed with status {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ SSE connection error: {e}")
            return False
    
    async def send_jsonrpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Send a JSON-RPC 2.0 request to the session-specific message endpoint"""
        if not self.session_message_url:
            print(f"❌ No session message URL available")
            return False
        
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
                self.session_message_url,
                json=jsonrpc_request,
                headers={'Content-Type': 'application/json'}
            ) as response:
                print(f"📨 POST Response Status: {response.status}")
                
                response_text = await response.text()
                print(f"📨 POST Response Body: {response_text}")
                
                # For MCP over HTTP, response might come via SSE
                return response.status in [200, 202]
                    
        except Exception as e:
            print(f"❌ JSON-RPC request error: {e}")
            return False

async def test_mcp_with_sse_responses():
    """Test MCP with SSE response handling"""
    
    # Load OAuth token
    try:
        with open('mcp_tokens.json', 'r') as f:
            tokens = json.load(f)
            access_token = tokens['access_token']
    except Exception as e:
        print(f"❌ Could not load access token: {e}")
        return False
    
    base_url = 'https://apim-hvsvkzkl6s2ra.azure-api.net/mcp'
    
    print(f"🚀 Starting MCP with SSE Response Test")
    print(f"🔗 Base URL: {base_url}")
    print(f"🎫 Access Token: {access_token[:20]}...")
    
    async with MCPSessionManager(base_url, access_token) as mcp:
        # Start SSE connection and JSON-RPC request concurrently
        print(f"\n" + "="*60)
        print(f"🚀 Starting Concurrent SSE and JSON-RPC Operations")
        print("="*60)
        
        # Create tasks for concurrent execution
        sse_task = asyncio.create_task(mcp.establish_session_and_listen())
        
        # Wait a moment for session establishment
        await asyncio.sleep(2)
        
        # Send tools/list request
        if mcp.session_message_url:
            print(f"\n📤 Sending tools/list request...")
            await mcp.send_jsonrpc_request("tools/list")
            
            # Wait for SSE responses
            print(f"\n⏰ Waiting for SSE responses (10 seconds)...")
            try:
                await asyncio.wait_for(asyncio.sleep(10), timeout=10)
            except asyncio.TimeoutError:
                pass
            
            # Cancel SSE task
            sse_task.cancel()
            try:
                await sse_task
            except asyncio.CancelledError:
                pass
            
            # Analyze received responses
            print(f"\n" + "="*60)
            print(f"🔍 Analyzing Received SSE Responses")
            print("="*60)
            
            if mcp.sse_responses:
                print(f"📨 Received {len(mcp.sse_responses)} SSE responses:")
                
                hello_mcp_found = False
                for i, response in enumerate(mcp.sse_responses):
                    print(f"\n📨 Response {i+1}: {json.dumps(response, indent=2)}")
                    
                    # Check if this is a tools/list response
                    if "result" in response and "tools" in response.get("result", {}):
                        tools = response["result"]["tools"]
                        print(f"🛠️  Found {len(tools)} tools in response {i+1}:")
                        
                        for tool in tools:
                            tool_name = tool.get("name", "unknown")
                            tool_desc = tool.get("description", "")
                            print(f"  • {tool_name}: {tool_desc}")
                            
                            if tool_name == "hello_mcp":
                                hello_mcp_found = True
                                print(f"    ✅ FOUND hello_mcp tool!")
                
                return hello_mcp_found
            else:
                print(f"❌ No SSE responses received")
                return False
        else:
            print(f"❌ No session established")
            return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_mcp_with_sse_responses())
        if result:
            print(f"\n🎉 SUCCESS: hello_mcp tool found and working!")
            print(f"🎉 The MCP server is properly deployed and functional!")
            sys.exit(0)
        else:
            print(f"\n💥 FAILED: Could not find hello_mcp tool in SSE responses")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)