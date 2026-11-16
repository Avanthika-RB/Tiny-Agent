"""Quick check of whether a model works for the helpdesk graphs, and how fast it is.

    python test_model.py nvidia/nemotron-3.5-lightning-30b-a3b

It tries the three things the graphs need: a plain reply, a tool call,
and structured output (what classify uses). Each test prints its time.
"""

import os
import sys
import time
from typing import Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from tools import get_ticket_status, lookup_employee

if len(sys.argv) != 2:
    raise SystemExit("Usage: python test_model.py <model-id>")

load_dotenv()
model = ChatOpenAI(
    model=sys.argv[1],
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
    temperature=0,
    max_retries=1,
)


class IntentSchema(BaseModel):
    intent: Literal["new_issue", "ticket_status", "password_reset", "other"]


def timed(label, fn):
    start = time.time()
    try:
        result = fn()
        print(f"[OK]   {label} ({time.time() - start:.1f}s): {result}")
    except Exception as error:
        print(f"[FAIL] {label} ({time.time() - start:.1f}s): {type(error).__name__}: {str(error)[:150]}")


timed("plain reply", lambda: model.invoke("Say hi in five words.").content)

timed(
    "tool call",
    lambda: model.bind_tools([lookup_employee, get_ticket_status])
    .invoke("Look up the employee priya.menon@example.com.")
    .tool_calls,
)

timed(
    "structured output",
    lambda: model.with_structured_output(IntentSchema, method="function_calling")
    .invoke("Any update on my ticket TKT-1001?"),
)
