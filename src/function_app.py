import json
import logging
from dataclasses import dataclass

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Constants for the Azure Blob Storage container, file, and blob path
_SNIPPET_NAME_PROPERTY_NAME = "snippetname"
_SNIPPET_PROPERTY_NAME = "snippet"
_BLOB_PATH = "snippets/{mcptoolargs." + _SNIPPET_NAME_PROPERTY_NAME + "}.json"

# Constants for BMI Calculator
_HEIGHT_FEET_PROPERTY_NAME = "height_feet"
_HEIGHT_INCHES_PROPERTY_NAME = "height_inches"
_WEIGHT_POUNDS_PROPERTY_NAME = "weight_pounds"


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

# BMI Calculator tool properties
tool_properties_bmi_calculator_object = [
    ToolProperty(_HEIGHT_FEET_PROPERTY_NAME, "integer", "Height in feet (e.g., 5 for 5'4\")"),
    ToolProperty(_HEIGHT_INCHES_PROPERTY_NAME, "integer", "Additional inches (e.g., 4 for 5'4\")"),
    ToolProperty(_WEIGHT_POUNDS_PROPERTY_NAME, "number", "Weight in pounds"),
]

# Convert the tool properties to JSON
tool_properties_save_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_save_snippets_object])
tool_properties_get_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_get_snippets_object])
tool_properties_bmi_calculator_json = json.dumps([prop.__dict__ for prop in tool_properties_bmi_calculator_object])


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


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="calculate_bmi",
    description="Calculate BMI using US measurements (feet/inches for height, pounds for weight).",
    toolProperties=tool_properties_bmi_calculator_json,
)
def calculate_bmi(context) -> str:
    """
    Calculates Body Mass Index (BMI) using US measurements.
    
    Args:
        context: The trigger context containing height and weight arguments.
        
    Returns:
        str: BMI calculation result with health category classification.
    """
    content = json.loads(context)
    if "arguments" not in content:
        return "No arguments provided"
    
    args = content["arguments"]
    height_feet = args.get(_HEIGHT_FEET_PROPERTY_NAME)
    height_inches = args.get(_HEIGHT_INCHES_PROPERTY_NAME) 
    weight_pounds = args.get(_WEIGHT_POUNDS_PROPERTY_NAME)
    
    # Validate inputs
    if height_feet is None:
        return "Height in feet is required"
    if height_inches is None:
        return "Height in inches is required"
    if weight_pounds is None:
        return "Weight in pounds is required"
        
    try:
        height_feet = int(height_feet)
        height_inches = int(height_inches)
        weight_pounds = float(weight_pounds)
    except (ValueError, TypeError):
        return "Invalid input: height_feet and height_inches must be integers, weight_pounds must be a number"
    
    # Validate ranges
    if height_feet < 0 or height_feet > 8:
        return "Height in feet must be between 0-8"
    if height_inches < 0 or height_inches >= 12:
        return "Height in inches must be between 0-11"
    if weight_pounds <= 0 or weight_pounds > 1000:
        return "Weight must be between 1-1000 pounds"
    
    # Convert to total inches then to meters
    total_inches = (height_feet * 12) + height_inches
    height_meters = total_inches * 0.0254
    
    # Convert pounds to kilograms
    weight_kg = weight_pounds * 0.453592
    
    # Calculate BMI
    bmi = weight_kg / (height_meters ** 2)
    
    # Determine BMI category
    if bmi < 18.5:
        category = "Underweight"
        category_emoji = "⚠️"
    elif bmi < 25:
        category = "Normal weight"
        category_emoji = "✅"
    elif bmi < 30:
        category = "Overweight" 
        category_emoji = "⚠️"
    else:
        category = "Obese"
        category_emoji = "🔴"
    
    # Create detailed response
    result = f"""BMI Calculation Results:
📏 Height: {height_feet}'{height_inches}" ({total_inches} inches / {height_meters:.2f}m)
⚖️ Weight: {weight_pounds:g} lbs ({weight_kg:.1f} kg)
📊 BMI: {bmi:.1f}
{category_emoji} Category: {category}

BMI Categories:
• Underweight: < 18.5
• Normal weight: 18.5 - 24.9
• Overweight: 25.0 - 29.9
• Obese: ≥ 30.0

Note: BMI is a screening tool and doesn't diagnose body fatness or health. 
Consult healthcare professionals for personalized health advice."""
    
    logging.info("BMI calculated: %.1f for %d'%d\" %s lbs", bmi, height_feet, height_inches, weight_pounds)
    return result
