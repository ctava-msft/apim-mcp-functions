#!/usr/bin/env python3
"""
Unit tests for Sentinel Agent functions
"""

import sys
import os
import json
from unittest.mock import Mock
from datetime import datetime

# Add src directory to path to import function_app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from function_app import validate_sentinel_payload, generate_ai_insights, SentinelIncident, SentinelEntity, SentinelAlertContext


def test_validate_sentinel_payload():
    """Test payload validation function"""
    print("🧪 Testing validate_sentinel_payload...")
    
    # Valid payload
    valid_payload = {
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
    
    incident = validate_sentinel_payload(valid_payload)
    assert incident is not None, "Valid payload should return incident object"
    assert incident.incidentId == "12345", "Incident ID should match"
    assert incident.severity == "High", "Severity should match"
    assert len(incident.entities) == 2, "Should have 2 entities"
    assert incident.entities[0].type == "Account", "First entity type should be Account"
    assert incident.entities[0].name == "user@domain.com", "First entity name should match"
    print("   ✅ Valid payload test passed")
    
    # Invalid payload - missing field
    invalid_payload = {
        "incidentId": "12345",
        "severity": "High"
        # Missing entities and alertContext
    }
    
    incident = validate_sentinel_payload(invalid_payload)
    assert incident is None, "Invalid payload should return None"
    print("   ✅ Invalid payload test passed")
    
    # Invalid payload - malformed entities
    malformed_payload = {
        "incidentId": "12345",
        "severity": "High",
        "entities": [
            {"type": "Account"}  # Missing name
        ],
        "alertContext": {
            "description": "Test",
            "timestamp": "2025-09-26T18:44:12Z"
        }
    }
    
    incident = validate_sentinel_payload(malformed_payload)
    assert incident is None, "Malformed payload should return None"
    print("   ✅ Malformed entities test passed")


def test_generate_ai_insights():
    """Test AI insights generation function"""
    print("🧪 Testing generate_ai_insights...")
    
    # High severity incident
    high_severity_incident = SentinelIncident(
        incidentId="12345",
        severity="High",
        entities=[
            SentinelEntity(type="Account", name="user@domain.com"),
            SentinelEntity(type="Host", name="host01")
        ],
        alertContext=SentinelAlertContext(
            description="Suspicious login detected",
            timestamp="2025-09-26T18:44:12Z"
        )
    )
    
    recommendations = generate_ai_insights(high_severity_incident)
    assert recommendations.confidenceScore >= 0.8, f"High severity should have high confidence, got {recommendations.confidenceScore}"
    assert len(recommendations.recommendations) > 0, "Should have recommendations"
    assert any("user@domain.com" in rec for rec in recommendations.recommendations), "Should mention the account"
    assert any("host01" in rec for rec in recommendations.recommendations), "Should mention the host"
    print("   ✅ High severity incident test passed")
    
    # Medium severity incident
    medium_severity_incident = SentinelIncident(
        incidentId="67890",
        severity="Medium",
        entities=[
            SentinelEntity(type="IP", name="192.168.1.100")
        ],
        alertContext=SentinelAlertContext(
            description="Unusual network traffic",
            timestamp="2025-09-26T18:44:12Z"
        )
    )
    
    recommendations = generate_ai_insights(medium_severity_incident)
    assert 0.5 <= recommendations.confidenceScore <= 0.8, f"Medium severity should have medium confidence, got {recommendations.confidenceScore}"
    assert len(recommendations.recommendations) > 0, "Should have recommendations"
    print("   ✅ Medium severity incident test passed")
    
    # Critical malware incident
    critical_incident = SentinelIncident(
        incidentId="11111",
        severity="Critical",
        entities=[
            SentinelEntity(type="Host", name="workstation-05"),
            SentinelEntity(type="Account", name="admin@company.com")
        ],
        alertContext=SentinelAlertContext(
            description="Malicious file detected with lateral movement indicators",
            timestamp="2025-09-26T18:44:12Z"
        )
    )
    
    recommendations = generate_ai_insights(critical_incident)
    assert recommendations.confidenceScore >= 0.8, f"Critical severity should have high confidence, got {recommendations.confidenceScore}"
    assert len(recommendations.recommendations) > 0, "Should have recommendations"
    assert 'threat_category' in recommendations.enrichment, "Should have threat category enrichment"
    print("   ✅ Critical malware incident test passed")


def test_ai_logic_patterns():
    """Test specific AI logic patterns"""
    print("🧪 Testing AI logic patterns...")
    
    # Test login-related incident
    login_incident = SentinelIncident(
        incidentId="login-01",
        severity="High",
        entities=[SentinelEntity(type="Account", name="test@example.com")],
        alertContext=SentinelAlertContext(
            description="Suspicious login activity detected",
            timestamp="2025-09-26T18:44:12Z"
        )
    )
    
    recommendations = generate_ai_insights(login_incident)
    assert any("MFA" in rec for rec in recommendations.recommendations), "Login incidents should recommend MFA"
    assert recommendations.enrichment.get('threat_category') == 'Authentication Attack', "Should categorize as authentication attack"
    print("   ✅ Login incident pattern test passed")
    
    # Test malware-related incident
    malware_incident = SentinelIncident(
        incidentId="malware-01",
        severity="Critical",
        entities=[SentinelEntity(type="Host", name="pc-01")],
        alertContext=SentinelAlertContext(
            description="Malware detected on endpoint",
            timestamp="2025-09-26T18:44:12Z"
        )
    )
    
    recommendations = generate_ai_insights(malware_incident)
    assert recommendations.enrichment.get('threat_category') == 'Malware Activity', "Should categorize as malware activity"
    assert any("antivirus" in rec.lower() for rec in recommendations.recommendations), "Should recommend antivirus scan"
    print("   ✅ Malware incident pattern test passed")


def run_all_tests():
    """Run all unit tests"""
    print("🚀 Starting Sentinel Agent Unit Tests")
    print("-" * 50)
    
    try:
        test_validate_sentinel_payload()
        test_generate_ai_insights()
        test_ai_logic_patterns()
        
        print("-" * 50)
        print("✅ All unit tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)