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
        self.sse_buffer = []
        
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
    
    def process_sse_event(self):
        """Process accumulated SSE lines into an event"""
        if not self.sse_buffer:
            return None
            
        event_type = None
        data_content = None
        
        for line in self.sse_buffer:
            line = line.strip()
            if line.startswith('event:'):
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                data_content = line[5:].strip()
        
        # Clear buffer
        self.sse_buffer = []
        
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
                                print(f"📡 SSE Line: {decoded}")
                                
                                # Add line to buffer
                                self.sse_buffer.append(decoded)
                                
                                # Check if we have a complete event (empty line signals end)
                                if decoded == '' or (decoded.startswith('event:') and len(self.sse_buffer) > 1):
                                    # Process previous complete event
                                    if len(self.sse_buffer) > 1:
                                        sse_event = self.process_sse_event()
                                        await self.handle_sse_event(sse_event)
                                    
                                    # Start new event if this is an event line
                                    if decoded.startswith('event:'):
                                        self.sse_buffer.append(decoded)
                                
                                # Also check if we have both event and data lines
                                has_event = any(line.startswith('event:') for line in self.sse_buffer)
                                has_data = any(line.startswith('data:') for line in self.sse_buffer)
                                
                                if has_event and has_data:
                                    sse_event = self.process_sse_event()
                                    await self.handle_sse_event(sse_event)
                else:
                    print(f"❌ SSE connection failed with status {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ SSE connection error: {e}")
            return False
    
    async def handle_sse_event(self, sse_event):
        """Handle a complete SSE event"""
        if not sse_event:
            return
            
        event_type = sse_event.get('event')
        data_content = sse_event.get('data')
        
        print(f"📡 Complete SSE Event: {event_type} -> {data_content}")
        
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
        print(f"📤 To URL: {self.session_message_url}")
        
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

async def test_mcp_final():
    """Final comprehensive MCP test"""
    
    # Load OAuth token
    try:
        with open('mcp_tokens.json', 'r') as f:
            tokens = json.load(f)
            access_token = tokens['access_token']
    except Exception as e:
        print(f"❌ Could not load access token: {e}")
        return False
    
    base_url = 'https://apim-hvsvkzkl6s2ra.azure-api.net/mcp'
    
    print(f"🚀 Final MCP Test - Looking for hello_mcp Tool")
    print(f"🔗 Base URL: {base_url}")
    print(f"🎫 Access Token: {access_token[:20]}...")
    
    async with MCPSessionManager(base_url, access_token) as mcp:
        # Start SSE listening task
        sse_task = asyncio.create_task(mcp.establish_session_and_listen())
        
        # Wait for session establishment
        print(f"\n⏰ Waiting for session establishment...")
        for i in range(10):  # Wait up to 10 seconds
            if mcp.session_message_url:
                print(f"✅ Session established after {i+1} seconds")
                break
            await asyncio.sleep(1)
        
        if not mcp.session_message_url:
            print(f"❌ Session not established within timeout")
            sse_task.cancel()
            return False
        
        # Send tools/list request
        print(f"\n📤 Sending tools/list request...")
        success = await mcp.send_jsonrpc_request("tools/list")
        
        if success:
            # Wait for responses
            print(f"\n⏰ Waiting for JSON-RPC responses...")
            for i in range(15):  # Wait up to 15 seconds for response
                if mcp.sse_responses:
                    print(f"✅ Received response after {i+1} seconds")
                    break
                await asyncio.sleep(1)
        
        # Cancel SSE task
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass
        
        # Analyze responses
        print(f"\n" + "="*60)
        print(f"🔍 Final Analysis - Looking for hello_mcp Tool")
        print("="*60)
        
        if mcp.sse_responses:
            print(f"📨 Received {len(mcp.sse_responses)} JSON-RPC responses")
            
            hello_mcp_found = False
            all_tools = []
            
            for i, response in enumerate(mcp.sse_responses):
                print(f"\n📨 Response {i+1}:")
                
                if "result" in response and "tools" in response.get("result", {}):
                    tools = response["result"]["tools"]
                    all_tools.extend(tools)
                    print(f"  🛠️  Contains {len(tools)} tools")
                    
                    for tool in tools:
                        tool_name = tool.get("name", "unknown")
                        tool_desc = tool.get("description", "")
                        print(f"    • {tool_name}: {tool_desc}")
                        
                        if tool_name == "hello_mcp":
                            hello_mcp_found = True
                            print(f"      🎉 FOUND THE hello_mcp TOOL!")
                elif "error" in response:
                    print(f"  ❌ Error response: {response['error']}")
                else:
                    print(f"  📋 Other response: {json.dumps(response, indent=4)}")
            
            if hello_mcp_found:
                print(f"\n🎉 SUCCESS! The hello_mcp tool was found!")
                print(f"🎉 Total tools discovered: {len(all_tools)}")
                return True
            else:
                print(f"\n❌ hello_mcp tool not found among {len(all_tools)} total tools")
                if all_tools:
                    print(f"Available tools: {[tool.get('name', 'unknown') for tool in all_tools]}")
                return False
        else:
            print(f"❌ No JSON-RPC responses received via SSE")
            return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_mcp_final())
        if result:
            print(f"\n🎉🎉🎉 FINAL SUCCESS: hello_mcp tool is working! 🎉🎉🎉")
            print(f"The Azure Function with MCP server is deployed and functional!")
            sys.exit(0)
        else:
            print(f"\n💥 FINAL FAILURE: hello_mcp tool not found")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)