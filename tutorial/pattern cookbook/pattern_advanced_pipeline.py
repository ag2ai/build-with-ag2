import json
from typing import Optional
from pydantic import BaseModel, Field
from autogen import (
    ConversableAgent,
    UserProxyAgent,
    LLMConfig,
)
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import DefaultPattern
from autogen.agentchat.group import AgentTarget, AgentNameTarget, OnContextCondition, ContextExpression, ExpressionContextCondition, ReplyResult, ContextVariables, RevertToUserTarget

# E-commerce order processing pipeline
# Each agent handles a specific stage of order processing in sequence

# Setup LLM configuration
llm_config = LLMConfig(config_list={"api_type": "openai", "model": "gpt-5-nano", "parallel_tool_calls": False, "cache_seed": None})

# Shared context for tracking order processing state
shared_context = ContextVariables(data={
    # Pipeline state
    "pipeline_started": False,
    "pipeline_completed": False,

    # Stage completion tracking
    "validation_completed": False,
    "inventory_completed": False,
    "payment_completed": False,
    "fulfillment_completed": False,
    "notification_completed": False,

    # Order data
    "order_details": {},
    "validation_results": {},
    "inventory_results": {},
    "payment_results": {},
    "fulfillment_results": {},
    "notification_results": {},

    # Error state
    "has_error": False,
    "error_message": "",
    "error_stage": ""
})

# Pydantic models for pipeline stages
class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Boolean indicating if the order passed validation")
    error_message: Optional[str] = Field(None, description="Explanation if validation failed")
    validation_details: Optional[dict] = Field(None, description="Any additional validation information")

class InventoryResult(BaseModel):
    items_available: bool = Field(..., description="Boolean indicating if all items are available")
    error_message: Optional[str] = Field(None, description="Explanation if any items are out of stock")
    reserved_items: Optional[list] = Field(None, description="Details of items reserved for this order")

class PaymentResult(BaseModel):
    payment_successful: bool = Field(..., description="Boolean indicating if payment was processed successfully")
    error_message: Optional[str] = Field(None, description="Explanation if payment failed")
    transaction_details: Optional[dict] = Field(None, description="Details of the payment transaction")

class FulfillmentResult(BaseModel):
    fulfillment_instructions: str = Field(..., description="Detailed instructions for order fulfillment")
    shipping_details: str = Field(..., description="Information about shipping method, tracking, etc.")
    estimated_delivery: str = Field(..., description="Expected delivery timeframe")

class NotificationResult(BaseModel):
    notification_sent: bool = Field(..., description="Boolean indicating if notification was sent")
    notification_method: str = Field(..., description="Method used to notify the customer (email, SMS, etc.)")
    notification_content: str = Field(..., description="Content of the notification message")

# Pipeline stage functions
def start_order_processing(order_json: str, context_variables: ContextVariables) -> ReplyResult:
    """Start the order processing pipeline with provided order details JSON string"""
    context_variables["pipeline_started"] = True

    # Parse the order JSON
    try:
        order_details = json.loads(order_json)
        context_variables["order_details"] = order_details

        return ReplyResult(
            message=f"Order processing started for Order #{order_details.get('order_id', 'Unknown')}",
            context_variables=context_variables,
            target=AgentNameTarget("validation_agent")
        )
    except json.JSONDecodeError:
        context_variables["has_error"] = True
        context_variables["error_message"] = "Invalid order JSON format"
        context_variables["error_stage"] = "entry"

        return ReplyResult(
            message="Failed to process order: Invalid JSON format",
            context_variables=context_variables,
            target=RevertToUserTarget()
        )

def run_validation_check(context_variables: ContextVariables) -> str:
    """Run the validation check for the order"""
    return "Validation check completed successfully."

def complete_validation(validation_result: ValidationResult, context_variables: ContextVariables) -> ReplyResult:
    """Complete the validation stage and pass to inventory check"""
    # Store the validation result in context variables
    context_variables["validation_results"] = validation_result.model_dump()
    context_variables["validation_completed"] = True

    # Check if validation failed
    if not validation_result.is_valid:
        context_variables["has_error"] = True
        context_variables["error_message"] = validation_result.error_message or "Validation failed"
        context_variables["error_stage"] = "validation"

        return ReplyResult(
            message=f"Validation failed: {validation_result.error_message or 'Unknown error'}",
            context_variables=context_variables,
            target=RevertToUserTarget()
        )

    return ReplyResult(
        message="Order validated successfully. Proceeding to inventory check.",
        context_variables=context_variables,
        target=AgentNameTarget("inventory_agent")
    )

def run_inventory_check(context_variables: ContextVariables) -> str:
    """Run the inventory check for the order"""
    return "Inventory check completed successfully."

def complete_inventory_check(inventory_result: InventoryResult, context_variables: ContextVariables) -> ReplyResult:
    """Complete the inventory check stage and pass to payment processing"""
    # Store the inventory result in context variables
    context_variables["inventory_results"] = inventory_result.model_dump()
    context_variables["inventory_completed"] = True

    # Check if inventory check failed
    if not inventory_result.items_available:
        context_variables["has_error"] = True
        context_variables["error_message"] = inventory_result.error_message or "Inventory check failed"
        context_variables["error_stage"] = "inventory"

        return ReplyResult(
            message=f"Inventory check failed: {inventory_result.error_message or 'Unknown error'}",
            context_variables=context_variables,
            target=RevertToUserTarget()
        )

    return ReplyResult(
        message="Inventory check completed successfully. Proceeding to payment processing.",
        context_variables=context_variables,
        target=AgentNameTarget("payment_agent")
    )

def check_payment_info(context_variables: ContextVariables) -> str:
    """Check the payment information for the order"""
    return "Payment information verified successfully."

def complete_payment_processing(payment_result: PaymentResult, context_variables: ContextVariables) -> ReplyResult:
    """Complete the payment processing stage and pass to fulfillment"""
    # Store the payment result in context variables
    context_variables["payment_results"] = payment_result.model_dump()
    context_variables["payment_completed"] = True

    # Check if payment processing failed
    if not payment_result.payment_successful:
        context_variables["has_error"] = True
        context_variables["error_message"] = payment_result.error_message or "Payment processing failed"
        context_variables["error_stage"] = "payment"

        return ReplyResult(
            message=f"Payment processing failed: {payment_result.error_message or 'Unknown error'}",
            context_variables=context_variables,
            target=RevertToUserTarget()
        )

    return ReplyResult(
        message="Payment processed successfully. Proceeding to order fulfillment.",
        context_variables=context_variables,
        target=AgentNameTarget("fulfillment_agent")
    )

def complete_fulfillment(fulfillment_result: FulfillmentResult, context_variables: ContextVariables) -> ReplyResult:
    """Complete the fulfillment stage and pass to notification"""
    # Store the fulfillment result in context variables
    context_variables["fulfillment_results"] = fulfillment_result.model_dump()
    context_variables["fulfillment_completed"] = True

    return ReplyResult(
        message="Order fulfillment completed. Proceeding to customer notification.",
        context_variables=context_variables,
        target=AgentNameTarget("notification_agent")
    )

def complete_notification(notification_result: NotificationResult, context_variables: ContextVariables) -> ReplyResult:
    """Complete the notification stage and finish the pipeline"""
    # Store the notification result in context variables
    context_variables["notification_results"] = notification_result.model_dump()
    context_variables["notification_completed"] = True
    context_variables["pipeline_completed"] = True

    return ReplyResult(
        message="Customer notification sent. Order processing completed successfully.",
        context_variables=context_variables,
        target=RevertToUserTarget()
    )

# Pipeline agents
entry_agent = ConversableAgent(
    name="entry_agent",
    system_message="""You are the entry point for the e-commerce order processing pipeline.
    Your task is to receive the order details and start the order processing.

    When you receive an order in JSON format, you should:
    1. Extract the full JSON string from the message
    2. Use the start_order_processing tool with the complete JSON string
    3. Do not modify or reformat the JSON

    The order details will be in a valid JSON format containing information about the customer, items, payment, etc.""",
    functions=[start_order_processing],
    llm_config=llm_config
)

validation_agent = ConversableAgent(
    name="validation_agent",
    system_message="""You are the validation stage of the order processing pipeline.

    Your specific role is to validate the order details before further processing.
    Focus on:
    - Running a validation check, using the run_validation_check tool

    When submitting your results, create a ValidationResult object with:
    - is_valid: boolean indicating if the order passed validation
    - error_message: explanation if validation failed (optional)
    - validation_details: any additional validation information (optional)

    Always use the run_validation_check tool before using the complete_validation tool to submit your ValidationResult and move the order to the next stage.""",
    functions=[run_validation_check, complete_validation],
    llm_config=llm_config
)

inventory_agent = ConversableAgent(
    name="inventory_agent",
    system_message="""You are the inventory stage of the order processing pipeline.

    Your specific role is to check if all items in the order are available in inventory.
    Focus on:
    - Running an inventory check using the run_inventory_check tool
    - Verifying each item's availability
    - Checking if requested quantities are in stock
    - Reserving the items for this order
    - Updating inventory counts

    When submitting your results, create an InventoryResult object with:
    - items_available: boolean indicating if all items are available
    - error_message: explanation if any items are out of stock (optional)
    - reserved_items: details of items reserved for this order (optional)

    Always use the run_inventory_check tool to do an inventory check before using the complete_inventory_check tool to submit your InventoryResult and move the order to the next stage.""",
    functions=[run_inventory_check, complete_inventory_check],
    llm_config=llm_config
)

payment_agent = ConversableAgent(
    name="payment_agent",
    system_message="""You are the payment processing stage of the order processing pipeline.

    Your specific role is to process the payment for the order.
    Focus on:
    - Running the check_payment_info tool to check the validity of the payment information
    - Verifying payment information
    - Processing the payment transaction
    - Recording payment details
    - Handling payment errors or rejections

    When submitting your results, create a PaymentResult object with:
    - payment_successful: boolean indicating if payment was processed successfully
    - error_message: explanation if payment failed (optional)
    - transaction_details: details of the payment transaction (optional)

    Always use the check_payment_info tool before running the complete_payment_processing tool to submit your PaymentResult and move the order to the next stage.""",
    functions=[check_payment_info, complete_payment_processing],
    llm_config=llm_config
)

fulfillment_agent = ConversableAgent(
    name="fulfillment_agent",
    system_message="""You are the fulfillment stage of the order processing pipeline.

    Your specific role is to create fulfillment instructions for the order.
    Focus on:
    - Creating picking instructions for warehouse staff
    - Generating shipping labels
    - Selecting appropriate packaging
    - Determining shipping method based on customer selection

    When submitting your results, create a FulfillmentResult object with:
    - fulfillment_instructions: detailed instructions for order fulfillment
    - shipping_details: information about shipping method, tracking, etc.
    - estimated_delivery: expected delivery timeframe

    Always use the complete_fulfillment tool to submit your FulfillmentResult and move the order to the next stage.""",
    functions=[complete_fulfillment],
    llm_config=llm_config
)

notification_agent = ConversableAgent(
    name="notification_agent",
    system_message="""You are the notification stage of the order processing pipeline.

    Your specific role is to notify the customer about their order status.
    Focus on:
    - Creating a clear order confirmation message
    - Including all relevant order details
    - Providing shipping and tracking information
    - Setting expectations for next steps

    When submitting your results, create a NotificationResult object with:
    - notification_sent: boolean indicating if notification was sent
    - notification_method: method used to notify the customer (email, SMS, etc.)
    - notification_content: content of the notification message

    Always use the complete_notification tool to submit your NotificationResult and complete the order processing pipeline.""",
    functions=[complete_notification],
    llm_config=llm_config
)

# User agent for interaction
user = UserProxyAgent(
    name="user",
    code_execution_config=False
)

# Register handoffs for the pipeline
# Entry agent starts the pipeline
entry_agent.handoffs.add_context_condition(
    OnContextCondition(
        target=AgentTarget(validation_agent),
        condition=ExpressionContextCondition(ContextExpression("${pipeline_started} == True and ${validation_completed} == False"))
    ),
)
entry_agent.handoffs.set_after_work(RevertToUserTarget())

# Validation agent passes to Inventory agent if validation succeeds
validation_agent.handoffs.set_after_work(RevertToUserTarget())

# Inventory agent passes to Payment agent if inventory check succeeds
inventory_agent.handoffs.set_after_work(RevertToUserTarget())

# Payment agent passes to Fulfillment agent if payment succeeds
payment_agent.handoffs.set_after_work(RevertToUserTarget())

# Fulfillment agent passes to Notification agent
fulfillment_agent.handoffs.set_after_work(AgentTarget(notification_agent))

# Notification agent finishes the pipeline and returns to user
notification_agent.handoffs.set_after_work(RevertToUserTarget())

# Run the pipeline
def run_pipeline_pattern():
    """Run the pipeline pattern for e-commerce order processing"""
    print("Initiating Pipeline Pattern for E-commerce Order Processing...")

    # Sample order to process
    sample_order = {
        "order_id": "ORD-12345",
        "customer": {
            "id": "CUST-789",
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "555-123-4567",
            "shipping_address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip": "90210",
                "country": "USA"
            },
            "billing_address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip": "90210",
                "country": "USA"
            }
        },
        "order_items": [
            {
                "item_id": "PROD-001",
                "name": "Smartphone XYZ",
                "quantity": 1,
                "price": 699.99
            },
            {
                "item_id": "PROD-042",
                "name": "Phone Case",
                "quantity": 2,
                "price": 24.99
            }
        ],
        "shipping_method": "express",
        "payment_info": {
            "method": "credit_card",
            "card_last_four": "4242",
            "amount": 749.97,
            "currency": "USD"
        },
        "promocode": "SUMMER10",
        "order_date": "2025-03-08T14:30:00Z"
    }

    sample_order_json = json.dumps(sample_order)

    agent_pattern = DefaultPattern(
        initial_agent=entry_agent,
        agents=[
            entry_agent,
            validation_agent,
            inventory_agent,
            payment_agent,
            fulfillment_agent,
            notification_agent
        ],
        user_agent=user,
        context_variables=shared_context,
    )

    chat_result, final_context, last_agent = initiate_group_chat(
        pattern=agent_pattern,
        messages=f"Please process this order through the pipeline:\n\n{sample_order_json}",
        max_rounds=30,
    )

    if final_context["pipeline_completed"]:
        print("Order processing completed successfully!")
        print("\n===== ORDER PROCESSING SUMMARY =====\n")
        print(f"Order ID: {final_context['order_details'].get('order_id')}")
        print(f"Customer: {final_context['order_details'].get('customer', {}).get('name')}")
        print(f"Total Amount: ${final_context['order_details'].get('payment_info', {}).get('amount')}")

        # Show the progression through pipeline stages
        print("\n===== PIPELINE PROGRESSION =====\n")
        print(f"Validation: {'✅ Passed' if final_context['validation_results'].get('is_valid') else '❌ Failed'}")
        print(f"Inventory: {'✅ Available' if final_context['inventory_results'].get('items_available') else '❌ Unavailable'}")
        print(f"Payment: {'✅ Successful' if final_context['payment_results'].get('payment_successful') else '❌ Failed'}")
        print(f"Fulfillment: {'✅ Completed' if 'fulfillment_results' in final_context else '❌ Not reached'}")
        print(f"Notification: {'✅ Sent' if final_context['notification_results'].get('notification_sent') else '❌ Not sent'}")

        # Display shipping information
        if 'fulfillment_results' in final_context:
            print("\n===== SHIPPING INFORMATION =====\n")
            print(f"Shipping Method: {final_context['fulfillment_results'].get('shipping_details', '')}")
            print(f"Estimated Delivery: {final_context['fulfillment_results'].get('estimated_delivery')}")

        print("\n\n===== SPEAKER ORDER =====\n")
        for message in chat_result.chat_history:
            if "name" in message and message["name"] != "_Group_Tool_Executor":
                print(f"{message['name']}")
    else:
        print("Order processing did not complete successfully.")
        if final_context["has_error"]:
            print(f"Error during {final_context['error_stage']} stage: {final_context['error_message']}")

if __name__ == "__main__":
    run_pipeline_pattern()