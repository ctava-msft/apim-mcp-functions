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

# Convert the tool properties to JSON
tool_properties_save_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_save_snippets_object])
tool_properties_get_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_get_snippets_object])


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


# Sentinel Agent functionality
@dataclass
class SentinelEntity:
    type: str
    name: str

@dataclass
class SentinelAlertContext:
    description: str
    timestamp: str

@dataclass
class SentinelIncident:
    incidentId: str
    severity: str
    entities: list[SentinelEntity]
    alertContext: SentinelAlertContext

@dataclass
class SentinelRecommendation:
    recommendations: list[str]
    confidenceScore: float
    enrichment: dict[str, Any]


def validate_sentinel_payload(payload: dict[str, Any]) -> SentinelIncident | None:
    """
    Validates the incoming Sentinel payload structure.
    
    Args:
        payload: The JSON payload from Sentinel Playbook
        
    Returns:
        SentinelIncident object if valid, None if invalid
    """
    try:
        # Validate required fields
        required_fields = ['incidentId', 'severity', 'entities', 'alertContext']
        for field in required_fields:
            if field not in payload:
                logging.error(f"Missing required field: {field}")
                return None
        
        # Validate entities structure
        entities = []
        for entity in payload.get('entities', []):
            if 'type' not in entity or 'name' not in entity:
                logging.error("Invalid entity structure - missing type or name")
                return None
            entities.append(SentinelEntity(type=entity['type'], name=entity['name']))
        
        # Validate alert context
        alert_context = payload.get('alertContext', {})
        if 'description' not in alert_context or 'timestamp' not in alert_context:
            logging.error("Invalid alertContext structure")
            return None
        
        return SentinelIncident(
            incidentId=payload['incidentId'],
            severity=payload['severity'],
            entities=entities,
            alertContext=SentinelAlertContext(
                description=alert_context['description'],
                timestamp=alert_context['timestamp']
            )
        )
    except Exception as e:
        logging.error(f"Error validating payload: {str(e)}")
        return None


def generate_ai_insights(incident: SentinelIncident) -> SentinelRecommendation:
    """
    Generates AI-driven insights and recommendations for a Sentinel incident.
    
    Args:
        incident: The validated Sentinel incident data
        
    Returns:
        SentinelRecommendation with insights and recommendations
    """
    recommendations = []
    enrichment = {}
    confidence_score = 0.0
    
    # Analyze severity and generate recommendations
    severity_lower = incident.severity.lower()
    
    if severity_lower in ['high', 'critical']:
        confidence_score = 0.9
        
        # Check for account entities
        accounts = [e for e in incident.entities if e.type.lower() == 'account']
        hosts = [e for e in incident.entities if e.type.lower() == 'host']
        
        if accounts:
            for account in accounts:
                recommendations.append(f"Disable account {account.name} immediately")
                recommendations.append(f"Reset password for account {account.name}")
                recommendations.append(f"Review recent login activity for {account.name}")
        
        if hosts:
            for host in hosts:
                recommendations.append(f"Isolate host {host.name} from network")
                recommendations.append(f"Run full antivirus scan on {host.name}")
                recommendations.append(f"Investigate {host.name} for lateral movement indicators")
        
        # Analyze alert context for suspicious patterns
        description_lower = incident.alertContext.description.lower()
        
        if 'login' in description_lower or 'logon' in description_lower:
            enrichment['threat_category'] = 'Authentication Attack'
            recommendations.append("Implement additional MFA requirements")
            
        if 'malicious' in description_lower or 'malware' in description_lower:
            enrichment['threat_category'] = 'Malware Activity'
            recommendations.append("Update endpoint protection signatures")
            
        if 'lateral' in description_lower or 'movement' in description_lower:
            enrichment['threat_category'] = 'Lateral Movement'
            recommendations.append("Review network segmentation policies")
            
        enrichment['threat_intel'] = "Incident requires immediate attention due to high severity"
        
    elif severity_lower == 'medium':
        confidence_score = 0.7
        recommendations.append("Monitor entities for 24 hours")
        recommendations.append("Review incident context for false positive indicators")
        enrichment['threat_intel'] = "Medium severity incident - monitor closely"
        
    else:  # Low severity
        confidence_score = 0.5
        recommendations.append("Log incident for trend analysis")
        recommendations.append("Schedule review within 48 hours")
        enrichment['threat_intel'] = "Low severity incident - routine monitoring"
    
    # Add timestamp-based recommendations
    try:
        incident_time = datetime.fromisoformat(incident.alertContext.timestamp.replace('Z', '+00:00'))
        current_time = datetime.now(incident_time.tzinfo)
        time_diff = current_time - incident_time
        
        if time_diff.total_seconds() > 3600:  # More than 1 hour old
            recommendations.append("Incident is over 1 hour old - verify current threat status")
            enrichment['time_analysis'] = "Delayed incident processing detected"
    except Exception as e:
        logging.warning(f"Could not parse timestamp: {str(e)}")
    
    return SentinelRecommendation(
        recommendations=recommendations,
        confidenceScore=confidence_score,
        enrichment=enrichment
    )


@app.function_name("sentinel_webhook")
@app.route(route="ai-agent/webhook", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def sentinel_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """
    Sentinel AI Agent webhook endpoint.
    
    Processes Sentinel Playbook incidents and returns AI-generated insights and recommendations.
    
    Args:
        req: HTTP request from Sentinel Playbook containing incident data
        
    Returns:
        JSON response with recommendations, confidence score, and enrichment data
    """
    try:
        # Log the incoming request
        logging.info(f"Sentinel webhook triggered with method: {req.method}")
        
        # Validate request method
        if req.method != 'POST':
            return func.HttpResponse(
                json.dumps({"error": "Only POST method is supported"}),
                status_code=405,
                mimetype="application/json"
            )
        
        # Parse request body
        try:
            payload = req.get_json()
            if not payload:
                return func.HttpResponse(
                    json.dumps({"error": "Request body must contain valid JSON"}),
                    status_code=400,
                    mimetype="application/json"
                )
        except Exception as e:
            logging.error(f"Failed to parse JSON payload: {str(e)}")
            return func.HttpResponse(
                json.dumps({"error": f"Invalid JSON format: {str(e)}"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Validate payload structure
        incident = validate_sentinel_payload(payload)
        if not incident:
            return func.HttpResponse(
                json.dumps({
                    "error": "Invalid payload structure. Required fields: incidentId, severity, entities, alertContext"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Log the validated incident
        logging.info(f"Processing Sentinel incident {incident.incidentId} with severity {incident.severity}")
        
        # Generate AI insights
        recommendations = generate_ai_insights(incident)
        
        # Prepare response
        response_data = {
            "recommendations": recommendations.recommendations,
            "confidenceScore": recommendations.confidenceScore,
            "enrichment": recommendations.enrichment,
            "processedAt": datetime.utcnow().isoformat() + "Z",
            "incidentId": incident.incidentId
        }
        
        # Log successful processing
        logging.info(
            f"Successfully processed incident {incident.incidentId} with "
            f"{len(recommendations.recommendations)} recommendations"
        )
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Unexpected error in sentinel_webhook: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error occurred while processing the request",
                "details": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
