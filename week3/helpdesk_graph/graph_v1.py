"""graph_v1: the Week 2 helpdesk agent, rebuilt as a hand-made LangGraph graph.

No create_agent. Same three tools, same model, same system prompt.

    python graph_v1.py                  chat in the terminal (type 'new' or 'quit')
    python graph_v1.py --demo "..."     run one message with invoke, then stream "updates", then stream "messages"
    python graph_v1.py --draw           save a picture of the graph to graph_v1.png
"""
import os
import sys
import uuid
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from tools import create_ticket, lookup_employee, search_known_issues

#MODEL = "nvidia/nemotron-3-super-120b-a12b"
#MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
RECURSION_LIMIT = 15

SYSTEM_PROMPT = """You are an IT helpdesk triage assistant for a company's Ops team.

Rules:
1. Always identify the employee first. If they have not given their work email, ask for it. Then call lookup_employee before doing anything else.
2. Try a known fix before filing a ticket. Use search_known_issues, and only share a fix if its "applies to" list includes the employee's OS. If no fix applies to their OS, say so and offer a ticket. Never make up your own fix steps.
3. Confirm with the user before creating a ticket. Tell them the summary and priority you plan to use, and only call create_ticket after they say yes.
4. Never invent ticket ids. Only report a ticket id that create_ticket returned.
5. Ticket priority must be low, medium, or high.
6. If the user says they already tried something that matches the known fix (even in different words), do not repeat the fix or ask if they tried it. Go straight to offering a ticket.
Keep replies short and friendly."""

TOOLS = [lookup_employee, search_known_issues, create_ticket]

#State: the data that flows through the graph.
class State(TypedDict):
    messages: Annotated[list, add_messages] # add_messages is reducer. node returns msgs and new msg is appended to list

load_dotenv()
api_key = os.environ.get("NVIDIA_API_KEY")
if not api_key:
    raise SystemExit("NVIDIA_API_KEY is not set. Add it to the .env file.")

model = ChatOpenAI(
    model=MODEL,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key,
    temperature=0,
    max_retries=5,
)
# bind_tools sends the tool descriptions with every model call (Week 1's tools=TOOLS).
model_with_tools = model.bind_tools(TOOLS)

#Nodes: take the state and return an update to it.
def call_model(state: State):
    # The system prompt is added here on every call and never stored in state.
    response = model_with_tools.invoke(
        [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    )
    # Returning a list under "messages" makes add_messages append it.
    return {"messages": [response]}

# ToolNode runs every tool call in the latest AI message and returns one
# ToolMessage per call (Week 1's run_tool + the tool messages.append).
tool_node = ToolNode(TOOLS)

#Graph: nodes plus the edges between them.
builder = StateGraph(State)
builder.add_node("call_model", call_model)
builder.add_node("tools", tool_node)

builder.add_edge(START, "call_model")
# tools_condition looks at the last message: if it has tool calls, go to
# "tools", otherwise go to END. This is Week 1's `if not message.tool_calls: break`.
builder.add_conditional_edges("call_model", tools_condition) #built in conditional edge
# After the tools run, always go back to the model. This edge is the loop.
builder.add_edge("tools", "call_model")

# The checkpointer saves state after every step, keyed by thread_id. this is for memory
graph = builder.compile(checkpointer=InMemorySaver())

#run graph
def new_config():
    return {
        "configurable": {"thread_id": str(uuid.uuid4())},
        "recursion_limit": RECURSION_LIMIT,
    }


def print_update(update):
    """Print one stream_mode="updates" chunk: {node_name: what that node returned}."""
    for node_name, node_output in update.items():
        for message in node_output["messages"]:
            if node_name == "call_model" and message.tool_calls:
                for call in message.tool_calls:
                    print(f"  [tool call] {call['name']}({call['args']})")
            elif node_name == "tools":
                result = str(message.content).replace("\n", "\n            ")
                print(f"  [result]    {result}")
            elif node_name == "call_model":
                print(f"\nAgent: {message.content}")


def chat():
    config = new_config()
    print("IT Helpdesk (graph_v1). Describe your problem.")
    print("Type 'new' to start a new conversation, or 'quit' to exit.")
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break
        if user_input.lower() == "new":
            config = new_config()
            print("(Started a new conversation.)")
            continue
        try:
            # stream_mode="updates" gives one chunk per node as it finishes,
            # so tool calls are printed as they happen.
            for update in graph.stream(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
                stream_mode="updates",
            ):
                print_update(update)
        except GraphRecursionError:
            print(f"\nAgent: Sorry, I couldn't finish that within {RECURSION_LIMIT} steps.")


def demo(message):
    """Run the same message three ways to compare invoke and the two stream modes."""
    user = {"messages": [{"role": "user", "content": message}]}

    print("=== 1. invoke: waits for the whole run, returns the final state ===")
    result = graph.invoke(user, config=new_config())
    print(f"{len(result['messages'])} messages in the final state. Last one:")
    print(result["messages"][-1].content)

    print('\n=== 2. stream_mode="updates": one chunk per node, as each node finishes ===')
    for update in graph.stream(user, config=new_config(), stream_mode="updates"):
        print(f"--- node finished: {list(update.keys())[0]}")
        print_update(update)

    print('\n=== 3. stream_mode="messages": the model\'s reply token by token ===')
    for chunk, metadata in graph.stream(user, config=new_config(), stream_mode="messages"):
        # Only print text coming from the model node, not the tool results.
        if metadata["langgraph_node"] == "call_model" and chunk.content:
            print(chunk.content, end="", flush=True)
    print()


def draw():
    # draw_mermaid_png sends the graph to the mermaid.ink website to render it
    png = graph.get_graph().draw_mermaid_png()
    path = Path(__file__).parent / "graph_v1.png"
    path.write_bytes(png)
    print(f"Saved {path}")

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--demo":
        demo(" ".join(sys.argv[2:]))
    elif len(sys.argv) == 2 and sys.argv[1] == "--draw":
        draw()
    else:
        chat()

#Notes to write: What did create_agent hide from you? List everything you had to write today.
# State class has a field messages. create_agent had its own state with list i never saw
# reducer tells langgraph to append new messages, instead of messages.append from before. 
# call_model is the model node that sends convo to model and returns reply, it has system prompt on each call wit messages instead of just system prompt before. 
# binding tools makes each request include tool descriptions, create agents did tis when passed tools=
# tools node runs every tool call te model asks for and returns result.
# edges like state, conditional edge, end having a tool loop. this is like if not messages.tool_calls: break
# compiling graph with checkpointer turns this into something runnable with memory. 
# instead of middleware to print, stream with stream_mode = updates and print what each node returns. 