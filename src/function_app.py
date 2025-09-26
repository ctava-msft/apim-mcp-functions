import json
import logging
from dataclasses import dataclass

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Constants for the Azure Blob Storage container, file, and blob path
_SNIPPET_NAME_PROPERTY_NAME = "snippetname"
_SNIPPET_PROPERTY_NAME = "snippet"
_BLOB_PATH = "snippets/{mcptoolargs." + _SNIPPET_NAME_PROPERTY_NAME + "}.json"

# Loan agent constants
_LOAN_POLICY_BLOB_PATH = "loan-policies/loan-policy.json"
_CUSTOMER_ID_PROPERTY = "customer_id"
_LOAN_APPLICATION_ID_PROPERTY = "application_id"
_VEHICLE_TYPE_PROPERTY = "vehicle_type"
_LOAN_AMOUNT_PROPERTY = "loan_amount"
_CREDIT_SCORE_PROPERTY = "credit_score"
_INCOME_PROPERTY = "annual_income"
_EMPLOYMENT_YEARS_PROPERTY = "employment_years"


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

# Loan agent tool properties
tool_properties_get_customer_history = [
    ToolProperty(_CUSTOMER_ID_PROPERTY, "string", "The unique customer identifier.")
]

tool_properties_get_risk_profile = [
    ToolProperty(_CUSTOMER_ID_PROPERTY, "string", "The unique customer identifier."),
    ToolProperty(_LOAN_AMOUNT_PROPERTY, "number", "The requested loan amount."),
    ToolProperty(_CREDIT_SCORE_PROPERTY, "number", "The customer's credit score.")
]

tool_properties_validate_loan_application = [
    ToolProperty(_LOAN_APPLICATION_ID_PROPERTY, "string", "The loan application ID."),
    ToolProperty(_CUSTOMER_ID_PROPERTY, "string", "The unique customer identifier."),
    ToolProperty(_LOAN_AMOUNT_PROPERTY, "number", "The requested loan amount."),
    ToolProperty(_VEHICLE_TYPE_PROPERTY, "string", "The type of vehicle being financed."),
    ToolProperty(_CREDIT_SCORE_PROPERTY, "number", "The customer's credit score."),
    ToolProperty(_INCOME_PROPERTY, "number", "The customer's annual income."),
    ToolProperty(_EMPLOYMENT_YEARS_PROPERTY, "number", "Years of employment history.")
]

tool_properties_calculate_loan_terms = [
    ToolProperty(_LOAN_AMOUNT_PROPERTY, "number", "The requested loan amount."),
    ToolProperty(_CREDIT_SCORE_PROPERTY, "number", "The customer's credit score."),
    ToolProperty(_VEHICLE_TYPE_PROPERTY, "string", "The type of vehicle being financed.")
]

tool_properties_get_special_vehicles = [
    ToolProperty(_VEHICLE_TYPE_PROPERTY, "string", "The type of vehicle to lookup.")
]

# Convert the tool properties to JSON
tool_properties_save_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_save_snippets_object])
tool_properties_get_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_get_snippets_object])

# Loan agent tool properties JSON
tool_properties_get_customer_history_json = json.dumps([prop.__dict__ for prop in tool_properties_get_customer_history])
tool_properties_get_risk_profile_json = json.dumps([prop.__dict__ for prop in tool_properties_get_risk_profile])
tool_properties_validate_loan_application_json = json.dumps(
    [prop.__dict__ for prop in tool_properties_validate_loan_application]
)
tool_properties_calculate_loan_terms_json = json.dumps([prop.__dict__ for prop in tool_properties_calculate_loan_terms])
tool_properties_get_special_vehicles_json = json.dumps([prop.__dict__ for prop in tool_properties_get_special_vehicles])


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


# Loan Agent MCP Tools

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_loan_policy",
    description="Retrieve loan approval policies and guidelines.",
    toolProperties="[]",
)
@app.generic_input_binding(arg_name="file", type="blob", connection="AzureWebJobsStorage", path=_LOAN_POLICY_BLOB_PATH)
def get_loan_policy(file: func.InputStream, context) -> str:
    """
    Retrieves loan approval policies from Azure Blob Storage.
    
    Returns:
        str: The loan policy document as JSON string or creates default policy.
    """
    try:
        policy_content = file.read().decode("utf-8")
        logging.info("Retrieved loan policy from storage")
        return policy_content
    except Exception as e:
        logging.warning(f"Loan policy not found in storage, returning default: {e}")
        # Return default loan policy
        default_policy = {
            "loan_policies": {
                "max_loan_amount": 100000,
                "min_credit_score": 600,
                "max_debt_to_income_ratio": 0.4,
                "min_employment_years": 2,
                "interest_rates": {
                    "excellent_credit": {"min_score": 750, "rate": 0.035},
                    "good_credit": {"min_score": 700, "rate": 0.045},
                    "fair_credit": {"min_score": 650, "rate": 0.065},
                    "poor_credit": {"min_score": 600, "rate": 0.085}
                },
                "vehicle_types": {
                    "new_car": {"max_loan_term": 72, "max_ltv": 0.9},
                    "used_car": {"max_loan_term": 60, "max_ltv": 0.8},
                    "luxury_vehicle": {"max_loan_term": 60, "max_ltv": 0.75},
                    "commercial_vehicle": {"max_loan_term": 48, "max_ltv": 0.7}
                },
                "special_conditions": {
                    "first_time_buyer_discount": 0.005,
                    "existing_customer_discount": 0.0025,
                    "automatic_approval_threshold": 800
                }
            }
        }
        return json.dumps(default_policy, indent=2)


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_customer_history",
    description="Retrieve customer banking and credit history.",
    toolProperties=tool_properties_get_customer_history_json,
)
def get_customer_history(context) -> str:
    """
    Retrieves customer banking and credit history.
    In a real implementation, this would query a database or external service.
    
    Args:
        context: The trigger context containing customer_id.
        
    Returns:
        str: Customer history as JSON string.
    """
    try:
        content = json.loads(context)
        if "arguments" not in content:
            return json.dumps({"error": "No arguments provided"})
            
        customer_id = content["arguments"].get(_CUSTOMER_ID_PROPERTY)
        if not customer_id:
            return json.dumps({"error": "Customer ID is required"})
            
        logging.info(f"Retrieving customer history for ID: {customer_id}")
        
        # Simulate customer history data
        # In production, this would query a real database
        customer_history = {
            "customer_id": customer_id,
            "credit_history": {
                "credit_score": 720,
                "credit_age_years": 8,
                "payment_history": "excellent",
                "total_accounts": 12,
                "open_accounts": 8,
                "credit_utilization": 0.25,
                "delinquencies": 0,
                "bankruptcies": 0
            },
            "banking_history": {
                "primary_bank_relationship_years": 5,
                "average_monthly_balance": 8500,
                "overdrafts_last_12_months": 0,
                "direct_deposit": True,
                "account_types": ["checking", "savings", "investment"]
            },
            "loan_history": {
                "previous_auto_loans": 2,
                "previous_auto_loan_performance": "excellent",
                "other_active_loans": 1,
                "total_monthly_obligations": 1200
            },
            "employment_verification": {
                "employer": "TechCorp Solutions",
                "position": "Senior Software Engineer",
                "employment_years": 4.5,
                "annual_income": 95000,
                "income_verification_date": "2024-09-01"
            }
        }
        
        return json.dumps(customer_history, indent=2)
        
    except Exception as e:
        logging.error(f"Error retrieving customer history: {e}")
        return json.dumps({"error": "Failed to retrieve customer history"})


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_risk_profile",
    description="Calculate comprehensive risk assessment for loan applications.",
    toolProperties=tool_properties_get_risk_profile_json,
)
def get_risk_profile(context) -> str:
    """
    Calculates a comprehensive risk profile for a loan application.
    
    Args:
        context: The trigger context containing customer_id, loan_amount, and credit_score.
        
    Returns:
        str: Risk assessment as JSON string.
    """
    try:
        content = json.loads(context)
        if "arguments" not in content:
            return json.dumps({"error": "No arguments provided"})
            
        args = content["arguments"]
        customer_id = args.get(_CUSTOMER_ID_PROPERTY)
        loan_amount = args.get(_LOAN_AMOUNT_PROPERTY)
        credit_score = args.get(_CREDIT_SCORE_PROPERTY)
        
        if not all([customer_id, loan_amount, credit_score]):
            return json.dumps({"error": "customer_id, loan_amount, and credit_score are required"})
            
        logging.info(f"Calculating risk profile for customer {customer_id}")
        
        # Calculate risk factors
        credit_risk = "low" if credit_score >= 750 else "medium" if credit_score >= 650 else "high"
        amount_risk = "low" if loan_amount <= 50000 else "medium" if loan_amount <= 80000 else "high"
        
        # Overall risk calculation
        risk_score = 0
        if credit_score >= 750:
            risk_score += 20
        elif credit_score >= 700:
            risk_score += 15
        elif credit_score >= 650:
            risk_score += 10
        else:
            risk_score += 5
            
        if loan_amount <= 30000:
            risk_score += 15
        elif loan_amount <= 60000:
            risk_score += 10
        else:
            risk_score += 5
            
        # Determine overall risk level
        overall_risk = "low" if risk_score >= 30 else "medium" if risk_score >= 20 else "high"
        
        # Calculate probability and recommended rate
        probability_of_default = 0.02 if overall_risk == "low" else 0.08 if overall_risk == "medium" else 0.15
        recommended_rate = 0.035 if overall_risk == "low" else 0.055 if overall_risk == "medium" else 0.085
        
        risk_profile = {
            "customer_id": customer_id,
            "loan_amount": loan_amount,
            "credit_score": credit_score,
            "risk_assessment": {
                "overall_risk_level": overall_risk,
                "risk_score": risk_score,
                "credit_risk": credit_risk,
                "amount_risk": amount_risk,
                "probability_of_default": probability_of_default,
                "recommended_interest_rate": recommended_rate
            },
            "risk_factors": {
                "positive_factors": [],
                "negative_factors": [],
                "mitigation_strategies": []
            },
            "assessment_date": "2024-09-26"
        }
        
        # Add specific risk factors based on profile
        if credit_score >= 750:
            risk_profile["risk_factors"]["positive_factors"].append("Excellent credit score")
        elif credit_score < 650:
            risk_profile["risk_factors"]["negative_factors"].append("Below average credit score")
            
        if loan_amount > 80000:
            risk_profile["risk_factors"]["negative_factors"].append("High loan amount")
            risk_profile["risk_factors"]["mitigation_strategies"].append("Consider larger down payment")
            
        return json.dumps(risk_profile, indent=2)
        
    except Exception as e:
        logging.error(f"Error calculating risk profile: {e}")
        return json.dumps({"error": "Failed to calculate risk profile"})


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_special_vehicles",
    description="Retrieve special vehicle information and financing terms.",
    toolProperties=tool_properties_get_special_vehicles_json,
)
def get_special_vehicles(context) -> str:
    """
    Retrieves special vehicle information and associated financing terms.
    
    Args:
        context: The trigger context containing vehicle_type.
        
    Returns:
        str: Special vehicle information as JSON string.
    """
    try:
        content = json.loads(context)
        if "arguments" not in content:
            return json.dumps({"error": "No arguments provided"})
            
        vehicle_type = content["arguments"].get(_VEHICLE_TYPE_PROPERTY)
        if not vehicle_type:
            return json.dumps({"error": "Vehicle type is required"})
            
        logging.info(f"Looking up special vehicle information for: {vehicle_type}")
        
        # Special vehicle database
        special_vehicles = {
            "luxury_vehicle": {
                "category": "luxury",
                "financing_terms": {
                    "max_loan_term_months": 60,
                    "max_ltv_ratio": 0.75,
                    "min_down_payment_percent": 25,
                    "interest_rate_adjustment": 0.005,
                    "special_requirements": ["Higher insurance coverage required", "Vehicle appraisal required"]
                },
                "eligible_makes": [
                    "BMW", "Mercedes-Benz", "Audi", "Lexus", "Porsche", "Tesla Model S", "Tesla Model X"
                ],
                "msrp_threshold": 60000
            },
            "commercial_vehicle": {
                "category": "commercial",
                "financing_terms": {
                    "max_loan_term_months": 48,
                    "max_ltv_ratio": 0.70,
                    "min_down_payment_percent": 30,
                    "interest_rate_adjustment": 0.010,
                    "special_requirements": [
                    "Business license verification", 
                    "Commercial insurance required", 
                    "Income verification from business"
                ]
                },
                "eligible_types": ["Pickup trucks over 1-ton", "Delivery vans", "Box trucks", "Flatbed trucks"],
                "additional_documentation": ["Business tax returns", "Commercial use affidavit"]
            },
            "electric_vehicle": {
                "category": "green",
                "financing_terms": {
                    "max_loan_term_months": 72,
                    "max_ltv_ratio": 0.85,
                    "min_down_payment_percent": 15,
                    "interest_rate_adjustment": -0.0025,
                    "special_incentives": ["Green vehicle discount", "Potential government rebates"]
                },
                "eligible_makes": ["Tesla", "Nissan Leaf", "Chevrolet Bolt", "Ford Mustang Mach-E", "Rivian"],
                "special_considerations": ["Battery warranty coverage", "Charging infrastructure assessment"]
            },
            "classic_vehicle": {
                "category": "specialty",
                "financing_terms": {
                    "max_loan_term_months": 48,
                    "max_ltv_ratio": 0.65,
                    "min_down_payment_percent": 35,
                    "interest_rate_adjustment": 0.015,
                    "special_requirements": [
                    "Professional appraisal required", 
                    "Specialized insurance", 
                    "Garage storage requirement"
                ]
                },
                "age_requirement": "25+ years old",
                "additional_documentation": ["Classic car appraisal", "Proof of secure storage"]
            }
        }
        
        vehicle_info = special_vehicles.get(vehicle_type.lower())
        if not vehicle_info:
            # Return general vehicle information
            return json.dumps({
                "vehicle_type": vehicle_type,
                "category": "standard",
                "financing_terms": {
                    "max_loan_term_months": 72,
                    "max_ltv_ratio": 0.85,
                    "min_down_payment_percent": 10,
                    "interest_rate_adjustment": 0.0,
                    "special_requirements": []
                },
                "message": "Standard financing terms apply"
            }, indent=2)
            
        vehicle_info["vehicle_type"] = vehicle_type
        return json.dumps(vehicle_info, indent=2)
        
    except Exception as e:
        logging.error(f"Error retrieving special vehicle information: {e}")
        return json.dumps({"error": "Failed to retrieve special vehicle information"})


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="validate_loan_application",
    description="Validate loan application data and check completeness.",
    toolProperties=tool_properties_validate_loan_application_json,
)
def validate_loan_application(context) -> str:
    """
    Validates a loan application for completeness and business rule compliance.
    
    Args:
        context: The trigger context containing loan application data.
        
    Returns:
        str: Validation results as JSON string.
    """
    try:
        content = json.loads(context)
        if "arguments" not in content:
            return json.dumps({"error": "No arguments provided"})
            
        args = content["arguments"]
        required_fields = [
            _LOAN_APPLICATION_ID_PROPERTY,
            _CUSTOMER_ID_PROPERTY,
            _LOAN_AMOUNT_PROPERTY,
            _VEHICLE_TYPE_PROPERTY,
            _CREDIT_SCORE_PROPERTY,
            _INCOME_PROPERTY,
            _EMPLOYMENT_YEARS_PROPERTY
        ]
        
        validation_result = {
            "application_id": args.get(_LOAN_APPLICATION_ID_PROPERTY),
            "is_valid": True,
            "validation_errors": [],
            "validation_warnings": [],
            "validation_summary": {
                "required_fields_complete": True,
                "business_rules_passed": True,
                "ready_for_processing": False
            }
        }
        
        # Check required fields
        missing_fields = []
        for field in required_fields:
            if not args.get(field):
                missing_fields.append(field)
                
        if missing_fields:
            validation_result["is_valid"] = False
            validation_result["validation_errors"].append(f"Missing required fields: {', '.join(missing_fields)}")
            validation_result["validation_summary"]["required_fields_complete"] = False
            
        # Business rule validations
        loan_amount = args.get(_LOAN_AMOUNT_PROPERTY, 0)
        credit_score = args.get(_CREDIT_SCORE_PROPERTY, 0)
        annual_income = args.get(_INCOME_PROPERTY, 0)
        employment_years = args.get(_EMPLOYMENT_YEARS_PROPERTY, 0)
        
        # Loan amount validation
        if loan_amount <= 0:
            validation_result["validation_errors"].append("Loan amount must be greater than 0")
            validation_result["is_valid"] = False
        elif loan_amount > 100000:
            validation_result["validation_warnings"].append(
                "Loan amount exceeds typical limits - may require additional approval"
            )
            
        # Credit score validation
        if credit_score < 300 or credit_score > 850:
            validation_result["validation_errors"].append("Credit score must be between 300 and 850")
            validation_result["is_valid"] = False
        elif credit_score < 600:
            validation_result["validation_warnings"].append(
                "Credit score below minimum threshold - high risk application"
            )
            
        # Income validation
        if annual_income <= 0:
            validation_result["validation_errors"].append("Annual income must be greater than 0")
            validation_result["is_valid"] = False
        elif annual_income < 30000:
            validation_result["validation_warnings"].append(
                "Low income relative to loan amount - debt-to-income ratio may be high"
            )
            
        # Employment validation
        if employment_years < 0:
            validation_result["validation_errors"].append("Employment years cannot be negative")
            validation_result["is_valid"] = False
        elif employment_years < 2:
            validation_result["validation_warnings"].append(
                "Short employment history - may require additional verification"
            )
            
        # Debt-to-income ratio check
        if loan_amount > 0 and annual_income > 0:
            estimated_monthly_payment = (loan_amount * 0.02)  # Rough estimate
            debt_to_income = (estimated_monthly_payment * 12) / annual_income
            if debt_to_income > 0.4:
                validation_result["validation_warnings"].append(f"High debt-to-income ratio: {debt_to_income:.2%}")
                
        # Final validation summary
        if validation_result["is_valid"] and len(validation_result["validation_errors"]) == 0:
            validation_result["validation_summary"]["ready_for_processing"] = True
            
        if len(validation_result["validation_errors"]) > 0:
            validation_result["validation_summary"]["business_rules_passed"] = False
            
        logging.info(f"Loan application validation completed for {args.get(_LOAN_APPLICATION_ID_PROPERTY)}")
        return json.dumps(validation_result, indent=2)
        
    except Exception as e:
        logging.error(f"Error validating loan application: {e}")
        return json.dumps({"error": "Failed to validate loan application"})


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="calculate_loan_terms",
    description="Calculate loan terms including interest rate and monthly payments.",
    toolProperties=tool_properties_calculate_loan_terms_json,
)
def calculate_loan_terms(context) -> str:
    """
    Calculates loan terms including interest rate, monthly payment, and total cost.
    
    Args:
        context: The trigger context containing loan_amount, credit_score, and vehicle_type.
        
    Returns:
        str: Calculated loan terms as JSON string.
    """
    try:
        content = json.loads(context)
        if "arguments" not in content:
            return json.dumps({"error": "No arguments provided"})
            
        args = content["arguments"]
        loan_amount = args.get(_LOAN_AMOUNT_PROPERTY)
        credit_score = args.get(_CREDIT_SCORE_PROPERTY)
        vehicle_type = args.get(_VEHICLE_TYPE_PROPERTY, "standard")
        
        if not all([loan_amount, credit_score]):
            return json.dumps({"error": "loan_amount and credit_score are required"})
            
        # Determine base interest rate based on credit score
        if credit_score >= 750:
            base_rate = 0.035  # 3.5%
        elif credit_score >= 700:
            base_rate = 0.045  # 4.5%
        elif credit_score >= 650:
            base_rate = 0.065  # 6.5%
        else:
            base_rate = 0.085  # 8.5%
            
        # Adjust rate based on vehicle type
        rate_adjustments = {
            "new_car": 0.0,
            "used_car": 0.005,
            "luxury_vehicle": 0.005,
            "commercial_vehicle": 0.010,
            "electric_vehicle": -0.0025,
            "classic_vehicle": 0.015
        }
        
        final_rate = base_rate + rate_adjustments.get(vehicle_type.lower(), 0.0)
        
        # Determine loan term based on vehicle type
        default_terms = {
            "new_car": 72,
            "used_car": 60,
            "luxury_vehicle": 60,
            "commercial_vehicle": 48,
            "electric_vehicle": 72,
            "classic_vehicle": 48
        }
        
        loan_term_months = default_terms.get(vehicle_type.lower(), 60)
        
        # Calculate monthly payment using standard loan formula
        # M = P * [r(1+r)^n] / [(1+r)^n - 1]
        monthly_rate = final_rate / 12
        num_payments = loan_term_months
        
        if monthly_rate == 0:
            monthly_payment = loan_amount / num_payments
        else:
            monthly_payment = (
                loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / 
                ((1 + monthly_rate) ** num_payments - 1)
            )
        
        total_payment = monthly_payment * num_payments
        total_interest = total_payment - loan_amount
        
        loan_terms = {
            "loan_amount": loan_amount,
            "credit_score": credit_score,
            "vehicle_type": vehicle_type,
            "loan_terms": {
                "interest_rate": round(final_rate * 100, 3),  # Convert to percentage
                "interest_rate_decimal": final_rate,
                "loan_term_months": loan_term_months,
                "monthly_payment": round(monthly_payment, 2),
                "total_payment": round(total_payment, 2),
                "total_interest": round(total_interest, 2),
                "apr": round(final_rate * 100, 3)  # Simplified APR calculation
            },
            "rate_breakdown": {
                "base_rate_percent": round(base_rate * 100, 3),
                "vehicle_adjustment_percent": round(rate_adjustments.get(vehicle_type.lower(), 0.0) * 100, 3),
                "final_rate_percent": round(final_rate * 100, 3)
            },
            "payment_schedule_summary": {
                "first_payment_date": "2024-10-26",  # Assumed 30 days from now
                "final_payment_date": "2030-10-26",  # Calculated based on term
                "payment_frequency": "monthly"
            },
            "calculation_date": "2024-09-26"
        }
        
        logging.info(f"Calculated loan terms for amount: ${loan_amount}, rate: {final_rate:.3%}")
        return json.dumps(loan_terms, indent=2)
        
    except Exception as e:
        logging.error(f"Error calculating loan terms: {e}")
        return json.dumps({"error": "Failed to calculate loan terms"})
