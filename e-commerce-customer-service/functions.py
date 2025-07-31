import json
from typing import Union
from autogen.agentchat.group import (
    ContextVariables,
    AgentNameTarget,
)
from autogen.agentchat.group import ReplyResult

with open("./mock_order_database.json") as f:
    MOCK_ORDER_DATABASE = json.load(f)

with open("mock_user_info.json") as f:
    MOCK_USER_INFO = json.load(f)


# for order management agent
def get_order_history(context_variables: ContextVariables) -> str:
    """Return the order history of the user."""
    order_str = ""
    orders = context_variables["user_info"]["orders"]
    if not orders:
        return "No order history found"
    for order_number, order in orders.items():
        order_str += f"Order Number: {order_number}, Product: {order['product']}, Status: {order['status']}, link: {order['link']}\n"
    return order_str


# for order management agent
def check_order_status(order_number: str, context_variables: ContextVariables) -> str:
    orders = context_variables["user_info"]["orders"]
    if order_number not in orders:
        return "The order number is invalid"
    return "The order is " + orders[order_number]["status"]


# for login agent
def login_account(context_variables: ContextVariables) -> Union[str, ReplyResult]:
    def mock_login_process():
        return True, MOCK_USER_INFO

    print("Mocking login process. User is successfully logged in.")
    login_in_status, user_info = mock_login_process()

    context_variables["user_info"] = user_info
    if login_in_status:
        user_preferrance_str = f"Name: {user_info['name']}, Preferred Name: {user_info['preferred_name']}, Preferred Language: {user_info['preferred_language']}, Preferred Tone: {user_info['preferred_tone']}"
        return ReplyResult(
            target=AgentNameTarget("order_management_agent"),
            message=f"User is successfully logged in. {user_preferrance_str}",
            context_variables=context_variables,
        )
    else:
        return "Failed to login. Please try again or ask for help to find your account/password."


# for return agent
def check_return_eligibility(
    order_number: str, context_variables: ContextVariables
) -> str:
    orders = context_variables["user_info"]["orders"]
    if order_number not in orders:
        return "The order number is invalid"
    if orders[order_number]["status"] != "delivered":
        return (
            "The order is not delivered yet, please wait until the order is delivered"
        )
    if orders[order_number]["return_status"] != "N/A":
        return "The order is already in return process"
    return "The order is eligible for return"


def initiate_return_process(
    order_number: str, context_variables: ContextVariables
) -> Union[str, ReplyResult]:
    orders = context_variables["user_info"]["orders"]
    if (
        not check_return_eligibility(order_number, context_variables)
        == "The order is eligible for return"
    ):
        return "The order is not eligible for return"

    orders[order_number]["return_status"] = "return_started"
    return f"The return process is initiated, click this link to get the return label: https://www.example.com/{order_number}/return_label"


# for tracking agent
def verify_order_number(
    order_number: str, context_variables: ContextVariables
) -> Union[str, ReplyResult]:
    # check the database to see if the order number is valid
    if order_number not in MOCK_ORDER_DATABASE:
        return "The order number is invalid"

    context_variables["order_number"] = order_number
    context_variables["order_info"] = MOCK_ORDER_DATABASE[order_number]
    return ReplyResult(
        message="The order number is valid.",
        context_variables=context_variables,
    )


# for tracking agent
def verify_user_information(
    email: str = None,
    phone_number_last_4_digit: str = None,
    context_variables: ContextVariables = None,
) -> str:
    if context_variables["order_info"] is None:
        return "An valid order number is not provided."

    order_info = context_variables["order_info"]
    order_str = f"Product: {order_info['product']}\nOrder Date: {order_info['order_date']}\nEstimated Delivery Date: {order_info['estimated_delivery_date']}\nCurrent Location: {order_info['current_location']}\n"

    if email:
        if email.strip() == context_variables["order_info"]["email"]:
            return order_str
    if phone_number_last_4_digit:
        if (
            phone_number_last_4_digit.strip()
            == context_variables["order_info"]["phone_number"][-4:]
        ):
            return order_str

    return "The email or phone number is invalid"
