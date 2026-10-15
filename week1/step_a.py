import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

MODEL = "nvidia/nemotron-3-super-120b-a12b"
SYSTEM_PROMPT = "You are a helpful assistant. Answer clearly and concisely."

# Get the question from the command line.
if len(sys.argv) < 2:
    raise SystemExit('Usage: python step_a.py "your question"')
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

# Send the system prompt and the question to the model.
response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ],
)

# Print the answer.
print(response.choices[0].message.content)
