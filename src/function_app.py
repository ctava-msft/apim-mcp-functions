from dataclasses import dataclass
import json
import logging
import os

import azure.functions as func
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import UserMessage
from azure.core.credentials import AzureKeyCredential

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Constants for the Azure Blob Storage container, file, and blob path
_SNIPPET_NAME_PROPERTY_NAME = "snippetname"
_SNIPPET_PROPERTY_NAME = "snippet"
_BLOB_PATH = "snippets/{mcptoolargs." + _SNIPPET_NAME_PROPERTY_NAME + "}.json"

# Constants for AI question-answering
_QUESTION_PROPERTY_NAME = "question"


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

tool_properties_ask_ai_object = [ToolProperty(_QUESTION_PROPERTY_NAME, "string", "The question to ask the AI model.")]

# Convert the tool properties to JSON
tool_properties_save_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_save_snippets_object])
tool_properties_get_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_get_snippets_object])
tool_properties_ask_ai_json = json.dumps([prop.__dict__ for prop in tool_properties_ask_ai_object])


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
    toolName="ask_ai",
    description="Ask a question to the AI language model and get an answer.",
    toolProperties=tool_properties_ask_ai_json,
)
def ask_ai(context) -> str:
    """
    Accepts a user's question and uses the Azure AI Inference language model to answer it.

    Args:
        context: The trigger context containing the input arguments.

    Returns:
        str: The AI model's response to the question or an error message.
    """
    try:
        content = json.loads(context)
        if "arguments" not in content:
            return "No arguments provided"

        question = content["arguments"].get(_QUESTION_PROPERTY_NAME)
        if not question:
            return "No question provided"

        # Get environment variables for AI service
        model_deployment_name = os.getenv("AGENTS_MODEL_DEPLOYMENT_NAME")
        if not model_deployment_name:
            return "AGENTS_MODEL_DEPLOYMENT_NAME environment variable not set"

        # Try to get the AI client using the pattern from the problem statement
        # This assumes there's some global client available or we need to create one
        try:
            # First try to use the pattern shown in the problem statement
            # Assuming 'client' might be available from some Azure SDK context
            # If not, fall back to direct ChatCompletionsClient
            
            # For Azure AI Inference, we need endpoint and credential
            endpoint = os.getenv("AZURE_AI_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_AI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
            
            if not endpoint:
                return "AZURE_AI_ENDPOINT or AZURE_OPENAI_ENDPOINT environment variable not set"
            if not api_key:
                return "AZURE_AI_API_KEY or AZURE_OPENAI_API_KEY environment variable not set"

            # Create the chat completions client directly
            chat_client = ChatCompletionsClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(api_key)
            )

            response = chat_client.complete(
                model=model_deployment_name,
                messages=[UserMessage(content=question)]
            )

            if response.choices and len(response.choices) > 0:
                answer = response.choices[0].message.content
                logging.info("AI question: %s, Answer: %s", question, answer)
                return answer
            else:
                return "No response received from AI model"

        except Exception as client_error:
            return f"Error initializing or calling AI client: {str(client_error)}"

    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        logging.error("Error in ask_ai function: %s", error_msg)
        return error_msg
