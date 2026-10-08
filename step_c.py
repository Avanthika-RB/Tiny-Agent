import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

MODEL = "nvidia/nemotron-3-super-120b-a12b"
SYSTEM_PROMPT = "You are a helpful assistant. Answer clearly and concisely."


# The tool: an ordinary Python function that returns fake weather data.
def get_weather(city):
    fake_weather = {
        "paris": "18C and cloudy",
        "tokyo": "24C and sunny",
        "seattle": "12C and rainy",
    }
    return fake_weather.get(city.lower(), "20C and clear")


# The second tool: works out a math expression such as "12 * 7".
def calculate(expression):
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed or "**" in expression: # <= subset of
        return "Error: only numbers and + - * / ( ) are allowed."
    try:
        return str(eval(expression)) #tool has to be a string
    except Exception as error:
        return f"Error: {error}"


# The descriptions of the tools that get sent to the model.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city, for example Paris.",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Work out a math expression and return the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The expression to work out, for example 12 * 7.",
                    },
                },
                "required": ["expression"],
            },
        },
    },
]


# Run whichever tool the model asked for
def run_tool(name, arguments):
    if name == "get_weather":
        return get_weather(arguments["city"])
    elif name == "calculate":
        return calculate(arguments["expression"])
    else:
        return f"Error: there is no tool called {name}."


# Get the question from the command line.
if len(sys.argv) < 2:
    raise SystemExit('Usage: python step_c.py "your question"')
question = " ".join(sys.argv[1:])

# Load the API key from the .env file.
load_dotenv()
api_key = os.environ.get("NVIDIA_API_KEY")
if not api_key:
    raise SystemExit("NVIDIA_API_KEY is not set. Add it to the .env file.")

# Connect to NVIDIA's endpoint.
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key,
)

# The conversation so far. It is a list so more messages can be added to it.
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": question},
]

MAX_ITERATIONS = 7

finished = False

for iterations in range(MAX_ITERATIONS):
    print("iteration", iterations + 1)
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        temperature=0,
    )
    message = response.choices[0].message
    #messages = list holding whole convo. message = last reply from model
    #if theres no tool call then print and break
    if not message.tool_calls:
        print(message.content)
        finished = True
        break
    messages.append(message)
    
    for tool_call in message.tool_calls:
        # Run the function with the arguments the model chose.
        arguments = json.loads(tool_call.function.arguments)
        result = run_tool(tool_call.function.name, arguments)
        print(f"[tool] {tool_call.function.name}({arguments}) returned {result!r}")

        # Add the result to the conversation, linked to the request by its id.
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            }
        )

if not finished:
    print("Exceeded amount of iterations. Iteration count:",MAX_ITERATIONS)


