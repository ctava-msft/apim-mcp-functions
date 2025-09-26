#!/usr/bin/env python3
"""
Quick OAuth2 URL Generator for MCP Server Testing
=================================================
"""

import sys
sys.path.append('.')
from test_mcp_server import OAuth2Client

def main():
    print("🔐 OAuth2 URL Generator for MCP Server")
    print("=====================================")
    
    # Initialize OAuth2 client
    oauth_client = OAuth2Client()
    
    # Register client if needed
    if not oauth_client.client_id:
        print("📝 Registering OAuth2 client...")
        if oauth_client.register_client():
            print(f"✅ Client registered: {oauth_client.client_id}")
        else:
            print("❌ Failed to register client")
            return
    else:
        print(f"✅ Using existing client: {oauth_client.client_id}")
    
    # Generate authorization URL
    auth_url = oauth_client.start_authorization_flow()
    
    if auth_url:
        print(f"\n🌐 Authorization URL Generated!")
        print(f"Copy this URL and open it in your browser:")
        print(f"{auth_url}")
        
        print(f"\n📋 Instructions:")
        print("1. Copy the URL above")
        print("2. Paste it in your browser")
        print("3. Complete the OAuth2 login flow")
        print("4. After redirect, copy the 'code' parameter from the callback URL")
        print("5. Use that code with the full test script (option 3)")
        
        print(f"\n💡 Next Steps:")
        print("- Run: python test_mcp_server.py")
        print("- Choose option 3 (Full OAuth2 flow)")
        print("- Paste the authorization code when prompted")
    else:
        print("❌ Failed to generate authorization URL")

if __name__ == "__main__":
    main()