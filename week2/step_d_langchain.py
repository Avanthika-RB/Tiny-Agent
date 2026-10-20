import os
import sys

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError

#MODEL = "nvidia/nemotron-3-super-120b-a12b"
MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
SYSTEM_PROMPT = "You are a helpful assistant. Answer clearly and concisely."
##SYSTEM_PROMPT = "You are a helpful assistant. Answer clearly and concisely. You also have a tool called get_time(city) that returns the local time in a city."

# LangGraph counts every step: each model call is one step and each round of
# tool calls is another. 13 steps allows 7 model calls, like MAX_ITERATIONS = 7 in Week 1.
RECURSION_LIMIT = 13


# Tool 1. The @tool decorator builds the description the model sees from the
# function name, the type hint (city: str) and the docstring.
@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The name of the city, for example Paris.
    """
    ##raise ConnectionError("weather service is down")
    fake_weather = {
        "paris": "18C and cloudy",
        "tokyo": "24C and sunny",
        "seattle": "12C and rainy",
    }
    return fake_weather.get(city.lower(), "20C and clear")
 # fix get_weather to call LLM/API for weather

# Tool 2.
@tool
def calculate(expression: str) -> str:
    """Work out a math expression and return the result.

    Args:
        expression: The expression to work out, for example 12 * 7.
    """
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed or "**" in expression:
        return "Error: only numbers and + - * / ( ) are allowed."
    try:
        return str(eval(expression))
    except Exception as error:
        return f"Error: {error}"


# Tool 3 (new this week).
@tool
def convert_temperature(celsius: float) -> str:
    """Convert a temperature from Celsius to Fahrenheit.

    Args:
        celsius: The temperature in degrees Celsius, for example 24.
    """
    fahrenheit = celsius * 9 / 5 + 32
    return f"{fahrenheit:.1f}F"


# Middleware that runs around every tool call, so each call is printed as it happens.
@wrap_tool_call
def print_tool_calls(request, handler):
    name = request.tool_call["name"]
    args = request.tool_call["args"]
    result = handler(request)  # this actually runs the tool
    print(f"[tool] {name}({args}) returned {result.content!r}")
    return result


# Get the question from the command line.
if len(sys.argv) < 2:
    raise SystemExit('Usage: python step_d_langchain.py "your question"')
question = " ".join(sys.argv[1:])

# Load the API key from the .env file.
load_dotenv()
api_key = os.environ.get("NVIDIA_API_KEY")
if not api_key:
    raise SystemExit("NVIDIA_API_KEY is not set. Add it to the .env file.")

# The same NVIDIA model as Week 1, through LangChain's OpenAI-compatible chat model.
model = ChatOpenAI(
    model=MODEL,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key,
    temperature=0,
)

# This replaces the Week 1 messages list, the for loop and run_tool().
agent = create_agent(
    model,
    tools=[get_weather, calculate, convert_temperature],
    system_prompt=SYSTEM_PROMPT,
    middleware=[print_tool_calls],
)

try:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": RECURSION_LIMIT},
    )
    print(result["messages"][-1].content)
except GraphRecursionError:
    print(f"Exceeded the recursion limit of {RECURSION_LIMIT} steps without a final answer.")
