#!/usr/bin/env python3
"""
Simple OAuth Token Endpoint Test
"""

import requests
import json

BASE_URL = "https://apim-hvsvkzkl6s2ra.azure-api.net"

def test_token_endpoint():
    """Test token endpoint with various payloads to debug the 500 error"""
    
    print("🔍 Testing Token Endpoint for Debugging")
    
    # Test 1: Minimal payload
    print("\n1. Testing with minimal payload...")
    try:
        response = requests.post(
            f"{BASE_URL}/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data="grant_type=authorization_code",
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Empty payload
    print("\n2. Testing with empty payload...")
    try:
        response = requests.post(
            f"{BASE_URL}/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data="",
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: With all expected parameters
    print("\n3. Testing with all expected parameters...")
    try:
        data = {
            "grant_type": "authorization_code",
            "code": "test_code_123",
            "code_verifier": "test_verifier_123",
            "client_id": "74f00413-f3a6-4354-a064-5d971d5c5138",
            "redirect_uri": "https://apim-hvsvkzkl6s2ra.azure-api.net/oauth-callback"
        }
        response = requests.post(
            f"{BASE_URL}/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_token_endpoint()