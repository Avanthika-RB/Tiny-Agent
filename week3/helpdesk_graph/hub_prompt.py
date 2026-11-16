"""Day 6: the supervisor's prompt in the LangSmith Prompt Hub.

    python hub_prompt.py push    push SUPERVISOR_PROMPT from graph_v5.py to the Hub as "helpdesk-supervisor"
    python hub_prompt.py pull    pull it back by name and print it (shows what the graph will use)

Then, to use the Hub version instead of the one in the code:
    1. Add PROMPT_FROM_HUB=1 to the .env file (or set it in the terminal).
    2. Run graph_v5.py as usual. It prints "Supervisor prompt: hub" at the start.
    3. Edit the prompt in LangSmith (Prompts > helpdesk-supervisor > Edit), commit it, and run
       graph_v5.py again. The new wording is used without changing any code.
Keep the two variables {conversation} and {worked} in the prompt when you edit it.
"""

import sys

from dotenv import load_dotenv

load_dotenv()


def main():
    from langsmith import Client
    from langsmith.utils import LangSmithConflictError
    client = Client()
    command = sys.argv[1:2]

    if command == ["push"]:
        import graph_v5
        try:
            url = client.push_prompt(
                graph_v5.PROMPT_NAME,
                object=graph_v5.SUPERVISOR_PROMPT,
                description="graph_v5 supervisor: picks triage, ticketops, or done. Variables: {conversation}, {worked}.",
            )
            print(f"Pushed {graph_v5.PROMPT_NAME}: {url}")
        except LangSmithConflictError:
            print("The Hub already has exactly this prompt, so there was nothing new to push.")
    elif command == ["pull"]:
        prompt = client.pull_prompt("helpdesk-supervisor")
        for message in prompt.messages:
            print(f"--- {type(message).__name__}\n{message.prompt.template}\n")
        print(f"Variables: {prompt.input_variables}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
