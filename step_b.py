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


# The description of the tool that gets sent to the model.
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
    }
]

# Get the question from the command line.
if len(sys.argv) < 2:
    raise SystemExit('Usage: python step_b.py "your question"')
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

# First call: the model either answers or asks for the tool.
response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=TOOLS,
    temperature=0,
)
message = response.choices[0].message

if message.tool_calls:
    # Add the model's tool request to the conversation.
    messages.append(message)

    for tool_call in message.tool_calls:
        # Run the function with the arguments the model chose.
        arguments = json.loads(tool_call.function.arguments)
        result = get_weather(arguments["city"])
        print(f"[tool] get_weather({arguments['city']!r}) returned {result!r}")

        # Add the result to the conversation, linked to the request by its id.
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            }
        )

    # Second call: the model now has the tool result and writes the answer.
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        temperature=0,
    )
    message = response.choices[0].message

# Print the final answer.
print(message.content)

#print(len(messages), "messages in the conversation")
#for m in messages:
#    print(m)
