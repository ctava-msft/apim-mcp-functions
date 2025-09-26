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
        self.session = None
        self.sse_response = None
        self.session_cookies = None
        self.session_message_url = None
        
    async def __aenter__(self):
        # Use cookie jar to maintain session state
        cookie_jar = aiohttp.CookieJar()
        self.session = aiohttp.ClientSession(
            cookie_jar=cookie_jar,
            headers={
                'Authorization': f'Bearer {self.auth_token}',
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.sse_response and not self.sse_response.closed:
            self.sse_response.close()
        if self.session:
            await self.session.close()
    
    async def establish_sse_session_properly(self) -> bool:
        """Establish SSE connection and keep it alive for session context"""
        try:
            print(f"🔗 Establishing SSE session to: {self.base_url}/sse")
            
            # Start the SSE connection
            self.sse_response = await self.session.get(
                f'{self.base_url}/sse',
                headers={
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive'
                }
            )
            
            print(f"📡 SSE Response Status: {self.sse_response.status}")
            print(f"📡 SSE Response Headers: {dict(self.sse_response.headers)}")
            
            # Capture cookies from SSE response
            if self.sse_response.cookies:
                print(f"🍪 SSE Response Cookies: {dict(self.sse_response.cookies)}")
            
            if self.sse_response.status == 200:
                # Try to read some initial data to trigger session establishment
                try:
                    # Read first chunk to ensure connection is established
                    async for chunk in self.sse_response.content.iter_chunked(1024):
                        if chunk:
                            data = chunk.decode('utf-8', errors='ignore')
                            print(f"📡 SSE Initial Data: {data[:200]}")
                            
                            # Parse the SSE data to extract session endpoint
                            if 'data: message?' in data:
                                # Extract the session URL from the SSE data
                                import re
                                match = re.search(r'data: (message\?[^\n\r]+)', data)
                                if match:
                                    session_path = match.group(1)
                                    self.session_message_url = f"{self.base_url}/{session_path}"
                                    print(f"🎯 Extracted session URL: {self.session_message_url}")
                            break
                        # Only wait for first chunk, then proceed
                        await asyncio.sleep(0.1)
                        break
                    
                    if self.session_message_url:
                        print("✅ SSE connection established with session URL")
                        return True
                    else:
                        print("⚠️  SSE connected but no session URL found")
                        return False
                        
                except Exception as e:
                    print(f"⚠️  SSE data read warning: {e}")
                    # Still consider successful if we got 200 status
                    await asyncio.sleep(1)
                    print("✅ SSE connection established (fallback)")
                    return True
            else:
                response_text = await self.sse_response.text()
                print(f"❌ SSE connection failed: {response_text}")
                return False
                
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
        
        # Use session-specific URL if available, otherwise fall back to generic endpoint
        message_url = self.session_message_url if self.session_message_url else f'{self.base_url}/message'
        print(f"🎯 Using message URL: {message_url}")
        
        try:
            async with self.session.post(
                message_url,
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
    
    async def listen_for_sse_response(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Listen for JSON-RPC response on the SSE stream"""
        if not self.sse_response:
            return None
            
        try:
            print(f"👂 Listening for SSE response (timeout: {timeout}s)...")
            
            async with asyncio.timeout(timeout):
                async for chunk in self.sse_response.content.iter_chunked(1024):
                    if chunk:
                        data = chunk.decode('utf-8', errors='ignore')
                        print(f"📡 SSE Response Data: {data}")
                        
                        # Look for JSON-RPC response in SSE data
                        if '"jsonrpc":"2.0"' in data or '"result"' in data:
                            # Try to extract JSON from SSE data
                            import re
                            json_match = re.search(r'data:\s*(\{.*\})', data, re.DOTALL)
                            if json_match:
                                try:
                                    json_response = json.loads(json_match.group(1))
                                    print(f"✅ Found JSON-RPC response in SSE stream")
                                    return json_response
                                except json.JSONDecodeError as e:
                                    print(f"⚠️  JSON decode error: {e}")
                                    continue
                        
                        # Continue listening for more data
                        await asyncio.sleep(0.1)
                        
        except asyncio.TimeoutError:
            print(f"⏰ SSE response timeout after {timeout}s")
        except Exception as e:
            print(f"❌ SSE response error: {e}")
            
        return None

async def test_mcp_fixed_session():
    """Test MCP with proper SSE session establishment"""
    
    # Load OAuth token
    try:
        with open('mcp_tokens.json', 'r') as f:
            tokens = json.load(f)
            access_token = tokens['access_token']
    except Exception as e:
        print(f"❌ Could not load access token: {e}")
        return False
    
    base_url = 'https://apim-hvsvkzkl6s2ra.azure-api.net/mcp'
    
    print(f"🚀 Starting Fixed MCP Session Test")
    print(f"🔗 Base URL: {base_url}")
    print(f"🎫 Access Token: {access_token[:20]}...")
    
    async with MCPSessionManager(base_url, access_token) as mcp:
        # Step 1: Establish SSE session first and keep it alive
        print("\n" + "="*50)
        print("📡 STEP 1: Establishing Persistent SSE Session")
        print("="*50)
        
        sse_success = await mcp.establish_sse_session_properly()
        if not sse_success:
            print("❌ SSE session failed, cannot continue")
            return False
        
        # Step 2: Wait a moment for session to be fully established
        print("\n⏰ Waiting for session to initialize...")
        await asyncio.sleep(2)
        
        # Step 3: Send tools/list request with active SSE session
        print("\n" + "="*50)
        print("🛠️  STEP 2: Sending tools/list Request (with active SSE)")
        print("="*50)
        
        # Send the request and check if it's accepted
        tools_response = await mcp.send_jsonrpc_request("tools/list")
        print(f"🛠️  Tools Response: {json.dumps(tools_response, indent=2)}")
        
        # If we got HTTP 202, listen for the actual response on SSE stream
        if tools_response.get("status") == 202:
            print("\n📡 HTTP 202 received - listening for response on SSE stream...")
            sse_json_response = await mcp.listen_for_sse_response()
            if sse_json_response:
                tools_response = sse_json_response
                print(f"🛠️  SSE Tools Response: {json.dumps(tools_response, indent=2)}")
        
        # Step 4: Check if hello_mcp tool is present
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
                return False
                
            # Step 4: Call the hello_mcp tool
            print("\n" + "="*50)
            print("🚀 STEP 4: Calling hello_mcp Tool")
            print("="*50)
            
            hello_response = await mcp.send_jsonrpc_request("tools/call", {
                "name": "hello_mcp",
                "arguments": {}
            })
            print(f"🛠️  Tool Call Response: {json.dumps(hello_response, indent=2)}")
            
            # If we got HTTP 202, listen for the actual response on SSE stream
            if hello_response.get("status") == 202:
                print("\n📡 HTTP 202 received - listening for tool response on SSE stream...")
                sse_tool_response = await mcp.listen_for_sse_response()
                if sse_tool_response:
                    hello_response = sse_tool_response
                    print(f"🛠️  SSE Tool Response: {json.dumps(hello_response, indent=2)}")
            
            # Check the tool call result
            if "result" in hello_response:
                result_content = hello_response["result"]
                print(f"✅ hello_mcp tool result: {result_content}")
                return True
            elif "error" in hello_response:
                print(f"❌ Tool call error: {hello_response['error']}")
                return False
                
            return hello_mcp_found
            
        elif "error" in tools_response:
            print(f"❌ JSON-RPC Error: {tools_response['error']}")
            return False
        else:
            print(f"❌ Unexpected response format")
            return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_mcp_fixed_session())
        if result:
            print(f"\n🎉 SUCCESS: hello_mcp tool found and called successfully!")
            sys.exit(0)
        else:
            print(f"\n💥 FAILED: Could not find or call hello_mcp tool")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        sys.exit(1)