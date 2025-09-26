#!/usr/bin/env python3
"""
Sentinel AI Agent Test Script

Tests the Sentinel webhook endpoint with various incident scenarios.

Usage:
    python test_sentinel_agent.py

Expected Output:
    ✅ All tests passed
    📊 Test results summary
"""

import json
import asyncio
import aiohttp
from typing import Dict, Any
import sys
from datetime import datetime

# Test data samples based on the issue requirements
SAMPLE_HIGH_SEVERITY_INCIDENT = {
    "incidentId": "12345",
    "severity": "High",
    "entities": [
        {"type": "Account", "name": "user@domain.com"},
        {"type": "Host", "name": "host01"}
    ],
    "alertContext": {
        "description": "Suspicious login detected",
        "timestamp": "2025-09-26T18:44:12Z"
    }
}

SAMPLE_MEDIUM_SEVERITY_INCIDENT = {
    "incidentId": "67890",
    "severity": "Medium",
    "entities": [
        {"type": "IP", "name": "192.168.1.100"}
    ],
    "alertContext": {
        "description": "Unusual network traffic pattern detected",
        "timestamp": "2025-09-26T19:30:00Z"
    }
}

SAMPLE_MALWARE_INCIDENT = {
    "incidentId": "11111",
    "severity": "Critical",
    "entities": [
        {"type": "Host", "name": "workstation-05"},
        {"type": "Account", "name": "admin@company.com"}
    ],
    "alertContext": {
        "description": "Malicious file detected with lateral movement indicators",
        "timestamp": "2025-09-26T20:15:30Z"
    }
}

INVALID_PAYLOAD_MISSING_FIELD = {
    "incidentId": "invalid-01",
    "severity": "High",
    # Missing entities and alertContext
}

INVALID_PAYLOAD_WRONG_STRUCTURE = {
    "incidentId": "invalid-02",
    "severity": "High",
    "entities": [
        {"type": "Account"}  # Missing name field
    ],
    "alertContext": {
        "description": "Test incident"
        # Missing timestamp
    }
}


class SentinelAgentTester:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = None
        self.test_results = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_webhook_endpoint(self, test_name: str, payload: Dict[str, Any], expected_status: int = 200) -> bool:
        """Test the webhook endpoint with given payload"""
        try:
            print(f"🧪 Testing: {test_name}")
            
            async with self.session.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                status_code = response.status
                response_text = await response.text()
                
                print(f"   Status: {status_code}")
                
                if status_code == expected_status:
                    if status_code == 200:
                        try:
                            response_data = json.loads(response_text)
                            self._validate_success_response(response_data)
                            print(f"   ✅ {test_name} - PASSED")
                            self.test_results.append({"test": test_name, "status": "PASSED", "response": response_data})
                            return True
                        except Exception as e:
                            print(f"   ❌ {test_name} - FAILED: Invalid response format: {str(e)}")
                            self.test_results.append({"test": test_name, "status": "FAILED", "error": str(e)})
                            return False
                    else:
                        print(f"   ✅ {test_name} - PASSED (Expected error status)")
                        self.test_results.append({"test": test_name, "status": "PASSED", "response": response_text})
                        return True
                else:
                    print(f"   ❌ {test_name} - FAILED: Expected {expected_status}, got {status_code}")
                    print(f"   Response: {response_text}")
                    self.test_results.append({"test": test_name, "status": "FAILED", "error": f"Status mismatch: {status_code}"})
                    return False

        except Exception as e:
            print(f"   ❌ {test_name} - FAILED: {str(e)}")
            self.test_results.append({"test": test_name, "status": "FAILED", "error": str(e)})
            return False

    def _validate_success_response(self, response_data: Dict[str, Any]):
        """Validate the structure of a successful response"""
        required_fields = ['recommendations', 'confidenceScore', 'enrichment', 'processedAt', 'incidentId']
        
        for field in required_fields:
            if field not in response_data:
                raise ValueError(f"Missing required field: {field}")
        
        if not isinstance(response_data['recommendations'], list):
            raise ValueError("recommendations must be a list")
        
        if not isinstance(response_data['confidenceScore'], (int, float)) or not (0 <= response_data['confidenceScore'] <= 1):
            raise ValueError("confidenceScore must be a number between 0 and 1")
        
        if not isinstance(response_data['enrichment'], dict):
            raise ValueError("enrichment must be an object")

    def print_test_results(self):
        """Print a summary of test results"""
        passed = sum(1 for result in self.test_results if result['status'] == 'PASSED')
        failed = sum(1 for result in self.test_results if result['status'] == 'FAILED')
        
        print(f"\n📊 Test Results Summary:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Success Rate: {(passed / len(self.test_results)) * 100:.1f}%")
        
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if result['status'] == 'FAILED':
                    print(f"   - {result['test']}: {result.get('error', 'Unknown error')}")

    async def run_all_tests(self):
        """Run all test scenarios"""
        print("🚀 Starting Sentinel AI Agent Tests")
        print(f"🔗 Testing endpoint: {self.webhook_url}")
        print("-" * 60)
        
        # Test valid high severity incident
        await self.test_webhook_endpoint(
            "High Severity Incident with Account and Host",
            SAMPLE_HIGH_SEVERITY_INCIDENT
        )
        
        # Test medium severity incident
        await self.test_webhook_endpoint(
            "Medium Severity Incident with IP",
            SAMPLE_MEDIUM_SEVERITY_INCIDENT
        )
        
        # Test critical malware incident
        await self.test_webhook_endpoint(
            "Critical Malware Incident with Lateral Movement",
            SAMPLE_MALWARE_INCIDENT
        )
        
        # Test invalid payload - missing fields
        await self.test_webhook_endpoint(
            "Invalid Payload - Missing Required Fields",
            INVALID_PAYLOAD_MISSING_FIELD,
            expected_status=400
        )
        
        # Test invalid payload - wrong structure
        await self.test_webhook_endpoint(
            "Invalid Payload - Wrong Entity Structure",
            INVALID_PAYLOAD_WRONG_STRUCTURE,
            expected_status=400
        )
        
        # Test non-JSON content type (if applicable)
        print(f"🧪 Testing: Non-JSON Content Type")
        try:
            async with self.session.post(
                self.webhook_url,
                data="not json",
                headers={'Content-Type': 'text/plain'},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 400:
                    print(f"   ✅ Non-JSON Content Type - PASSED")
                    self.test_results.append({"test": "Non-JSON Content Type", "status": "PASSED"})
                else:
                    print(f"   ❌ Non-JSON Content Type - FAILED: Expected 400, got {response.status}")
                    self.test_results.append({"test": "Non-JSON Content Type", "status": "FAILED"})
        except Exception as e:
            print(f"   ❌ Non-JSON Content Type - FAILED: {str(e)}")
            self.test_results.append({"test": "Non-JSON Content Type", "status": "FAILED", "error": str(e)})
        
        print("-" * 60)
        self.print_test_results()


async def main():
    # Default to localhost for local testing
    webhook_url = "http://localhost:7071/api/ai-agent/webhook"
    
    # Check if URL is provided as argument
    if len(sys.argv) > 1:
        webhook_url = sys.argv[1]
    
    print(f"Testing Sentinel AI Agent webhook at: {webhook_url}")
    print("To test against a deployed endpoint, run:")
    print("  python test_sentinel_agent.py https://your-apim-url/sentinel/ai-agent/webhook")
    print()
    
    async with SentinelAgentTester(webhook_url) as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())