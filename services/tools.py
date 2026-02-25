# services/tools.py
# Stateless tools the LLM agent can call.
# "Stateless" means they don't depend on which user or thread is calling them.
# They just do their job with the arguments the LLM passes.
#
# The @tool decorator does two things:
#   1. Reads the function's TYPE ANNOTATIONS to build a JSON schema the LLM understands
#   2. Reads the DOCSTRING to tell the LLM when and why to call this tool
# Both are critical. A missing docstring = LLM doesn't know when to use the tool.
# Missing type annotations = LLM doesn't know what arguments to pass.

import requests
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

from core.config import settings

# Pre-built LangChain tool — wraps DuckDuckGo search API
# Stateless and safe to share across all threads
search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform basic arithmetic on two numbers.
    Supported operations: add, sub, mul, div
    Use this for any mathematical calculation the user asks for.
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'. Use: add, sub, mul, div"}

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch the latest stock price for a given ticker symbol.
    Examples: 'AAPL' for Apple, 'TSLA' for Tesla, 'GOOGL' for Google.
    Use this when the user asks about a stock price or company valuation.
    """
    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}"
        f"&apikey={settings.alpha_vantage_api_key}"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}
