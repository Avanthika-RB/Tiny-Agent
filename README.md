
# Tiny Agent 

## 1. Concepts

### What an LLM is, and what actually happens when you "call" one through an API

LLMS have neural networks that predict the next word in a sequence, its was instinctive and didnt use a tree of reasoning, but that is something that will continue to be worked on for deep reasoning. LLMs are like an operating system that has different parts of the system where each has a specific task. Stage 1: pretraining. Stage 2: finetuning. When you call one through an API, you send a request with parametersm then theres tokenization, and recieve a response.

### Prompt vs. system prompt

System prompt conditions the behavior of the model, telling it what it can and cannot do and its not seen by the user. Prompt is what the user inputs. 

### Tokens and context window (and why they cost money)

Input is broken into pieces called tokens like words or characters, sound or image, and their position. Each token is associated with a vector that encodes the meaning of the piece. Context window determines how long of a convo the LLM can carry out without forgetting details from earlier. We measure context window size by tokens. Self attention computes vectors of weights where a weight is relevant to other tokens in sequence. Size of window determines max num of tokens the model can pay attention to any 1 time. Aa lot of things can be taking space in context window like the user input, model response, system prompt, docs, code, RAG. As num of input tokens doubles, then 4x more processing power to handle it. As context increases theres more computations, and thats why it determines how much money is spent on tokens. 

### Tool calling / function calling: what the model actually returns when it "calls" a tool, and who runs the tool

when you do a traditional tool calling where you have an llm and client app, you can see LLM hallucinate and it can also make wrong tool calls. So take embedded tool for a framework to interact with LLM and tool definitions. Instead of tool definitions and execution being from the application to llm, it will send to the library in the middle and can provide the final answer. Who runs the tools can be APIs, databases, or code.  When model colls a tool it returns text and parameters like what arguments it holds and the function being called. 

### Temperature, and why you'd keep it low for an agent

Temperature is a setting that controls randomness of the outputted words that you can set by doing temperature=0 so the model always picks the most likely/predictable word, a higher number increases the randomness and outputs the less likely words and has a lot of mistakes. 

## 2. Reflection

### If the task needed five different tools and the model had to pick the order, what would get hard? 

If I needed to add many tools then i would have to write a function for each tool and then add descriptions to the TOOLS that get sent to the model for each one. This can be difficult if theres a lot of different tools that need to be called in one file. This leads me to my next point that it was repetitive to write these tools multiple times and then update run_tools if you add even more tools to this assignment. One annoying thing was wording of variables like "message" vs "messages". 

#### If the script crashed halfway through a long run, what would you lose, and how might you avoid that?

To simulate the script crashing halfway through a long run, I gave a prompt of "Get the temperature in Tokyo. Multiply it by 3. Then add 10 to that. Then divide that by 2. Use the calculate tool separately for each step." This has 5 iterations. I stopped the first run after the first iteration, the memory is temporary and nothing was saved. I ran it again and it had to rerun from the beginning to the end because it was repeating what has already been done on the first iteration again. It lost the information from the first run/iteration because it isnt stored into memory permanently, it has a higher cost so the later you crash, the more you lose. To avoid this, the script could have the ability to store data permanently in case of a crash. 

### How would you know whether the agent gave a good answer or a bad one, across 100 different questions?

Depending on the type of question, its hard to define whether its a "good" or "bad" answer. A number like the temperature would be a definitive answer but theres answers to questions that arent just math and numbers, it can have opinions that dont have only 1 right answer. 