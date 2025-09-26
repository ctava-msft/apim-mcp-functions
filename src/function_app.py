import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Constants for the Azure Blob Storage container, file, and blob path
_SNIPPET_NAME_PROPERTY_NAME = "snippetname"
_SNIPPET_PROPERTY_NAME = "snippet"
_BLOB_PATH = "snippets/{mcptoolargs." + _SNIPPET_NAME_PROPERTY_NAME + "}.json"

# Security Event Constants
_SECURITY_EVENT_PROPERTY_NAME = "event"
_SEVERITY_PROPERTY_NAME = "severity"
_LIMIT_PROPERTY_NAME = "limit"
_INCIDENT_TYPE_PROPERTY_NAME = "incident_type"
_SECURITY_LOGS_PROPERTY_NAME = "logs"


@dataclass
class ToolProperty:
    propertyName: str
    propertyType: str
    description: str


# Define the tool properties using the ToolProperty class
tool_properties_save_snippets_object = [
    ToolProperty(_SNIPPET_NAME_PROPERTY_NAME, "string", "The name of the snippet."),
    ToolProperty(_SNIPPET_PROPERTY_NAME, "string", "The content of the snippet."),
]

tool_properties_get_snippets_object = [ToolProperty(_SNIPPET_NAME_PROPERTY_NAME, "string", "The name of the snippet.")]

# Security tool properties
tool_properties_analyze_threat_object = [
    ToolProperty(_SECURITY_EVENT_PROPERTY_NAME, "string", "Security event description to analyze for threats.")
]

tool_properties_query_events_object = [
    ToolProperty(_SEVERITY_PROPERTY_NAME, "string", 
                "Filter by severity level (critical, high, medium, low). Optional."),
    ToolProperty(_LIMIT_PROPERTY_NAME, "string", 
                "Maximum number of events to return (default: 10). Optional.")
]

tool_properties_incident_response_object = [
    ToolProperty(_INCIDENT_TYPE_PROPERTY_NAME, "string", 
                "Type of security incident (data_breach, malware, unauthorized_access, etc.)"),
    ToolProperty(_SEVERITY_PROPERTY_NAME, "string", 
                "Severity level of the incident (critical, high, medium, low)")
]

tool_properties_security_logs_object = [
    ToolProperty(_SECURITY_LOGS_PROPERTY_NAME, "string", "JSON array of security event logs to upload")
]

# Convert the tool properties to JSON
tool_properties_save_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_save_snippets_object])
tool_properties_get_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_get_snippets_object])

# Security tool properties JSON
tool_properties_analyze_threat_json = json.dumps([prop.__dict__ for prop in tool_properties_analyze_threat_object])
tool_properties_query_events_json = json.dumps([prop.__dict__ for prop in tool_properties_query_events_object])
tool_properties_incident_response_json = json.dumps([
    prop.__dict__ for prop in tool_properties_incident_response_object
])
tool_properties_security_logs_json = json.dumps([prop.__dict__ for prop in tool_properties_security_logs_object])


# Sample security events for demonstration (in production this would come from Cosmos DB)
SAMPLE_SECURITY_EVENTS = [
    {
        "id": "evt-001",
        "event_type": "authentication_failure",
        "severity": "high",
        "source_ip": "192.168.1.100",
        "target_resource": "database-server-01",
        "description": "Multiple failed login attempts detected",
        "timestamp": "2024-01-01T00:00:00Z",
        "user_account": "admin@company.com",
        "status": "investigating"
    },
    {
        "id": "evt-002",
        "event_type": "network_intrusion",
        "severity": "critical",
        "source_ip": "203.0.113.5",
        "target_resource": "web-server-02",
        "description": "Suspicious network activity detected on port 22",
        "timestamp": "2024-01-01T01:15:00Z",
        "user_account": "unknown",
        "status": "active"
    },
    {
        "id": "evt-003",
        "event_type": "data_access_violation",
        "severity": "medium",
        "source_ip": "10.0.0.50",
        "target_resource": "customer-database",
        "description": "Unauthorized access attempt to sensitive data",
        "timestamp": "2024-01-01T02:30:00Z",
        "user_account": "employee@company.com",
        "status": "resolved"
    }
]


def analyze_threat_with_ai(event_description: str) -> str:
    """
    Analyze security event using AI (simulated - in production would use Azure OpenAI).
    
    Args:
        event_description: Description of the security event to analyze
        
    Returns:
        AI analysis result as string
    """
    # In production, this would call Azure OpenAI GPT-4o
    # For now, we'll provide a simulated intelligent response
    
    if "failed login" in event_description.lower() or "authentication" in event_description.lower():
        return """🔍 THREAT ANALYSIS:
        
**Threat Level: HIGH**
**Category: Credential Attack**

**Analysis:**
- Pattern indicates potential brute force or credential stuffing attack
- Multiple failed authentication attempts suggest automated attack tools
- Recommend immediate IP blocking and account lockout policies

**Recommended Actions:**
1. Block source IP immediately
2. Enable account lockout after 3 failed attempts
3. Implement CAPTCHA for suspicious login patterns
4. Review authentication logs for similar patterns
5. Notify security team for investigation"""

    elif "network" in event_description.lower() or "port" in event_description.lower():
        return """🔍 THREAT ANALYSIS:
        
**Threat Level: CRITICAL**
**Category: Network Intrusion**

**Analysis:**
- Suspicious network activity detected
- Potential unauthorized access attempt
- Could indicate reconnaissance or active exploitation

**Recommended Actions:**
1. Immediately isolate affected systems
2. Block suspicious IP addresses at firewall level
3. Perform full network scan for compromise indicators
4. Review network logs for lateral movement
5. Initiate incident response procedures"""

    elif "data" in event_description.lower() or "access" in event_description.lower():
        return """🔍 THREAT ANALYSIS:
        
**Threat Level: MEDIUM-HIGH**
**Category: Data Security Violation**

**Analysis:**
- Unauthorized data access attempt detected
- Potential insider threat or compromised credentials
- Data exfiltration risk present

**Recommended Actions:**
1. Review user access permissions immediately
2. Audit data access logs for anomalies
3. Implement data loss prevention (DLP) controls
4. Investigate user account for compromise
5. Consider temporary access suspension"""

    else:
        return """🔍 THREAT ANALYSIS:
        
**Threat Level: MEDIUM**
**Category: General Security Event**

**Analysis:**
- Security event requires investigation
- Insufficient data for detailed threat classification
- Recommend manual review by security analyst

**Recommended Actions:**
1. Gather additional context and logs
2. Correlate with other security events
3. Review system and user activity patterns
4. Document findings for trend analysis
5. Consider enhancing monitoring coverage"""


def filter_security_events(severity: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """
    Filter security events by criteria.
    
    Args:
        severity: Filter by severity level
        limit: Maximum number of events to return
        
    Returns:
        List of filtered security events
    """
    events = SAMPLE_SECURITY_EVENTS.copy()
    
    if severity:
        events = [event for event in events if event.get("severity", "").lower() == severity.lower()]
    
    # Sort by timestamp (most recent first)
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return events[:limit]


def generate_incident_response_plan(incident_type: str, severity: str) -> str:
    """
    Generate incident response recommendations based on incident type and severity.
    
    Args:
        incident_type: Type of security incident
        severity: Severity level of the incident
        
    Returns:
        Incident response plan as string
    """
    severity_upper = severity.upper()
    
    base_plan = f"""🚨 INCIDENT RESPONSE PLAN
    
**Incident Type:** {incident_type.title()}
**Severity Level:** {severity_upper}
**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

"""
    
    if incident_type.lower() == "data_breach":
        plan = base_plan + """**IMMEDIATE ACTIONS (0-1 hours):**
1. ⚡ Isolate affected systems immediately
2. 📞 Notify incident response team lead
3. 🔒 Secure evidence and logs
4. 📋 Document initial findings
5. 🚨 Alert senior management if CRITICAL

**SHORT-TERM ACTIONS (1-24 hours):**
1. 🕵️ Conduct forensic analysis of breach scope
2. 📊 Assess data types and volume affected  
3. 🔍 Identify attack vectors and vulnerabilities
4. 📞 Prepare customer/stakeholder notifications
5. ⚖️ Review legal and regulatory requirements

**RECOVERY ACTIONS (1-7 days):**
1. 🔧 Patch vulnerabilities and strengthen security
2. 📢 Execute communication plan
3. 🏥 Restore systems from clean backups
4. 👥 Provide affected user support
5. 📝 Complete incident documentation"""

    elif incident_type.lower() == "malware":
        plan = base_plan + """**IMMEDIATE ACTIONS (0-1 hours):**
1. 🔌 Disconnect infected systems from network
2. 🛡️ Run full antimalware scans
3. 📋 Document malware indicators (IOCs)
4. 🔍 Check for lateral movement
5. 💾 Preserve system images for analysis

**SHORT-TERM ACTIONS (1-24 hours):**
1. 🧬 Analyze malware sample and behavior
2. 🔍 Hunt for additional infections
3. 🔒 Update security controls and signatures
4. 📊 Assess potential data compromise
5. 🚨 Coordinate with threat intelligence teams

**RECOVERY ACTIONS (1-7 days):**
1. 🧹 Clean and rebuild affected systems
2. 🔄 Restore from verified clean backups
3. 💪 Strengthen endpoint protection
4. 📚 Update security awareness training
5. 🔍 Implement enhanced monitoring"""

    elif incident_type.lower() == "unauthorized_access":
        plan = base_plan + """**IMMEDIATE ACTIONS (0-1 hours):**
1. 🔐 Disable compromised accounts immediately
2. 🔒 Reset passwords and revoke access tokens
3. 📋 Document unauthorized access details
4. 🔍 Check for privilege escalation
5. 📊 Review recent account activities

**SHORT-TERM ACTIONS (1-24 hours):**
1. 🕵️ Investigate access patterns and timeline
2. 🔍 Check for data exfiltration
3. 🛡️ Review and strengthen access controls
4. 📞 Verify identity of affected users
5. 🔒 Implement additional authentication factors

**RECOVERY ACTIONS (1-7 days):**
1. 🔄 Restore legitimate user access safely
2. 🏥 Review and update access policies
3. 👥 Conduct security awareness training
4. 🔍 Implement user behavior analytics
5. 📝 Document lessons learned"""

    else:
        plan = base_plan + """**IMMEDIATE ACTIONS (0-1 hours):**
1. 🚨 Assess and contain the incident
2. 📞 Notify appropriate response teams
3. 📋 Document initial observations
4. 🔒 Preserve evidence and logs
5. 🛡️ Implement temporary protective measures

**SHORT-TERM ACTIONS (1-24 hours):**
1. 🔍 Conduct detailed incident analysis
2. 📊 Determine scope and impact
3. 🔧 Identify and patch vulnerabilities
4. 📞 Coordinate with stakeholders
5. 📝 Prepare status reports

**RECOVERY ACTIONS (1-7 days):**
1. 🏥 Restore normal operations
2. 💪 Strengthen security controls
3. 📚 Update procedures and training
4. 🔍 Implement monitoring improvements
5. 📋 Complete incident report"""

    # Add severity-specific escalation procedures
    if severity_upper == "CRITICAL":
        plan += """

**🚨 CRITICAL SEVERITY ESCALATIONS:**
- Executive team notification within 15 minutes
- Consider external incident response support
- Prepare for potential public disclosure
- Coordinate with legal and PR teams
- Activate business continuity plans"""

    elif severity_upper == "HIGH":
        plan += """

**⚠️ HIGH SEVERITY ESCALATIONS:**
- Management notification within 1 hour
- Consider additional security resources
- Review customer communication needs
- Coordinate with compliance teams
- Prepare detailed impact assessment"""

    return plan


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="hello_mcp",
    description="Hello world.",
    toolProperties="[]",
)
def hello_mcp(context) -> str:
    """
    A simple function that returns a greeting message.

    Args:
        context: The trigger context (not used in this function).

    Returns:
        str: A greeting message.
    """
    return "Hello I am MCPTool!"


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_snippet",
    description="Retrieve a snippet by name.",
    toolProperties=tool_properties_get_snippets_json,
)
@app.generic_input_binding(arg_name="file", type="blob", connection="AzureWebJobsStorage", path=_BLOB_PATH)
def get_snippet(file: func.InputStream, context) -> str:
    """
    Retrieves a snippet by name from Azure Blob Storage.

    Args:
        file (func.InputStream): The input binding to read the snippet from Azure Blob Storage.
        context: The trigger context containing the input arguments.

    Returns:
        str: The content of the snippet or an error message.
    """
    snippet_content = file.read().decode("utf-8")
    logging.info("Retrieved snippet: %s", snippet_content)
    return snippet_content


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="save_snippet",
    description="Save a snippet with a name.",
    toolProperties=tool_properties_save_snippets_json,
)
@app.generic_output_binding(arg_name="file", type="blob", connection="AzureWebJobsStorage", path=_BLOB_PATH)
def save_snippet(file: func.Out[str], context) -> str:
    content = json.loads(context)
    if "arguments" not in content:
        return "No arguments provided"

    snippet_name_from_args = content["arguments"].get(_SNIPPET_NAME_PROPERTY_NAME)
    snippet_content_from_args = content["arguments"].get(_SNIPPET_PROPERTY_NAME)

    if not snippet_name_from_args:
        return "No snippet name provided"

    if not snippet_content_from_args:
        return "No snippet content provided"

    file.set(snippet_content_from_args)
    logging.info("Saved snippet: %s", snippet_content_from_args)
    return f"Snippet '{snippet_content_from_args}' saved successfully"


# Security Admin Agent MCP Tools


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="analyze_security_threat",
    description="Analyze security events and detect potential threats using AI",
    toolProperties=tool_properties_analyze_threat_json,
)
def analyze_security_threat(context) -> str:
    """
    Analyze security events and detect potential threats using AI analysis.
    
    Args:
        context: The trigger context containing the security event to analyze.
        
    Returns:
        str: AI-powered threat analysis results and recommendations.
    """
    try:
        content = json.loads(context)
        if "arguments" not in content:
            return "❌ No arguments provided"
        
        event_description = content["arguments"].get(_SECURITY_EVENT_PROPERTY_NAME)
        if not event_description:
            return "❌ No security event description provided"
        
        logging.info("Analyzing security threat for event: %s", event_description)
        
        # Analyze the threat using AI
        analysis_result = analyze_threat_with_ai(event_description)
        
        logging.info("Threat analysis completed successfully")
        return analysis_result
        
    except json.JSONDecodeError:
        return "❌ Invalid JSON in request context"
    except Exception as e:
        logging.error("Error analyzing security threat: %s", str(e))
        return f"❌ Error analyzing security threat: {str(e)}"


@app.generic_trigger(
    arg_name="context", 
    type="mcpToolTrigger",
    toolName="query_security_events",
    description="Query historical security events and incidents",
    toolProperties=tool_properties_query_events_json,
)
def query_security_events(context) -> str:
    """
    Query historical security events and incidents with optional filtering.
    
    Args:
        context: The trigger context containing query parameters.
        
    Returns:
        str: JSON formatted list of security events matching the query.
    """
    try:
        content = json.loads(context)
        arguments = content.get("arguments", {})
        
        severity = arguments.get(_SEVERITY_PROPERTY_NAME)
        limit_str = arguments.get(_LIMIT_PROPERTY_NAME, "10")
        
        try:
            limit = int(limit_str)
        except (ValueError, TypeError):
            limit = 10
            
        if limit > 100:
            limit = 100  # Prevent excessive queries
            
        logging.info("Querying security events with severity: %s, limit: %d", severity, limit)
        
        # Filter and retrieve security events
        events = filter_security_events(severity=severity, limit=limit)
        
        result = {
            "query_parameters": {
                "severity": severity,
                "limit": limit
            },
            "total_events": len(events),
            "events": events
        }
        
        logging.info("Retrieved %d security events", len(events))
        return json.dumps(result, indent=2)
        
    except json.JSONDecodeError:
        return "❌ Invalid JSON in request context"
    except Exception as e:
        logging.error("Error querying security events: %s", str(e))
        return f"❌ Error querying security events: {str(e)}"


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger", 
    toolName="generate_incident_response",
    description="Generate incident response recommendations based on threat analysis",
    toolProperties=tool_properties_incident_response_json,
)
def generate_incident_response(context) -> str:
    """
    Generate incident response recommendations based on incident type and severity.
    
    Args:
        context: The trigger context containing incident details.
        
    Returns:
        str: Detailed incident response plan and recommendations.
    """
    try:
        content = json.loads(context)
        if "arguments" not in content:
            return "❌ No arguments provided"
            
        incident_type = content["arguments"].get(_INCIDENT_TYPE_PROPERTY_NAME)
        severity = content["arguments"].get(_SEVERITY_PROPERTY_NAME)
        
        if not incident_type:
            return "❌ No incident type provided"
        if not severity:
            return "❌ No severity level provided"
            
        logging.info("Generating incident response for type: %s, severity: %s", incident_type, severity)
        
        # Generate incident response plan
        response_plan = generate_incident_response_plan(incident_type, severity)
        
        logging.info("Incident response plan generated successfully")
        return response_plan
        
    except json.JSONDecodeError:
        return "❌ Invalid JSON in request context"
    except Exception as e:
        logging.error("Error generating incident response: %s", str(e))
        return f"❌ Error generating incident response: {str(e)}"


# Additional HTTP endpoints for direct API access


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint for monitoring service availability.
    
    Args:
        req: HTTP request object
        
    Returns:
        HTTP response with health status
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "Security Admin Agent",
            "version": "1.0.0",
            "features": [
                "threat_analysis",
                "security_event_query", 
                "incident_response",
                "mcp_protocol_support"
            ]
        }
        
        return func.HttpResponse(
            json.dumps(health_status, indent=2),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        logging.error("Health check failed: %s", str(e))
        return func.HttpResponse(
            json.dumps({"status": "unhealthy", "error": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


@app.route(route="analyze-threat", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def analyze_threat_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint for threat analysis.
    
    Args:
        req: HTTP request containing security event data
        
    Returns:
        HTTP response with threat analysis results
    """
    try:
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "No JSON body provided"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
            
        event_description = req_body.get("event")
        if not event_description:
            return func.HttpResponse(
                json.dumps({"error": "No 'event' field provided"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
            
        analysis_result = analyze_threat_with_ai(event_description)
        
        return func.HttpResponse(
            json.dumps({"analysis": analysis_result}),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logging.error("Error in analyze-threat endpoint: %s", str(e))
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


@app.route(route="security-events", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def security_events_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint for querying security events.
    
    Args:
        req: HTTP request with optional query parameters
        
    Returns:
        HTTP response with security events
    """
    try:
        severity = req.params.get("severity")
        limit_str = req.params.get("limit", "10")
        
        try:
            limit = int(limit_str)
        except (ValueError, TypeError):
            limit = 10
            
        if limit > 100:
            limit = 100
            
        events = filter_security_events(severity=severity, limit=limit)
        
        result = {
            "query_parameters": {
                "severity": severity,
                "limit": limit
            },
            "total_events": len(events),
            "events": events
        }
        
        return func.HttpResponse(
            json.dumps(result, indent=2),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logging.error("Error in security-events endpoint: %s", str(e))
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


@app.route(route="incident-response", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def incident_response_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint for incident response plan generation.
    
    Args:
        req: HTTP request containing incident details
        
    Returns:
        HTTP response with incident response plan
    """
    try:
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "No JSON body provided"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
            
        incident_type = req_body.get("incident_type")
        severity = req_body.get("severity")
        
        if not incident_type:
            return func.HttpResponse(
                json.dumps({"error": "No 'incident_type' field provided"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
            
        if not severity:
            return func.HttpResponse(
                json.dumps({"error": "No 'severity' field provided"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
            
        response_plan = generate_incident_response_plan(incident_type, severity)
        
        return func.HttpResponse(
            json.dumps({"response_plan": response_plan}),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logging.error("Error in incident-response endpoint: %s", str(e))
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


@app.route(route="security-logs", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def security_logs_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint for uploading new security events.
    
    Args:
        req: HTTP request containing security log data
        
    Returns:
        HTTP response with upload status
    """
    try:
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "No JSON body provided"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
            
        logs = req_body.get("logs")
        if not logs:
            return func.HttpResponse(
                json.dumps({"error": "No 'logs' field provided"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
            
        if not isinstance(logs, list):
            return func.HttpResponse(
                json.dumps({"error": "'logs' must be an array"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
            
        # In production, this would store to Cosmos DB
        # For now, we'll just validate and acknowledge receipt
        processed_logs = []
        for i, log_entry in enumerate(logs):
            if isinstance(log_entry, dict):
                # Add timestamp if not present
                if "timestamp" not in log_entry:
                    log_entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
                processed_logs.append(log_entry)
            else:
                logging.warning("Skipping invalid log entry at index %d", i)
                
        result = {
            "status": "success",
            "message": f"Processed {len(processed_logs)} security log entries",
            "processed_count": len(processed_logs),
            "total_submitted": len(logs),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        logging.info("Processed %d security log entries", len(processed_logs))
        
        return func.HttpResponse(
            json.dumps(result, indent=2),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logging.error("Error in security-logs endpoint: %s", str(e))
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )
