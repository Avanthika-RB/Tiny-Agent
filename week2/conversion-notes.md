# Tiny Agent Week 2 - LangChain
## Conversion-notes

### Line count before vs after.
The line count from step_c was 142. The line count from step_d_langchain is 109.

### Which of your Week 1 lines disappeared entirely, and where did that logic go?
TOOLS list disappeared entirely and the logic went to putting @tool above each function which holds the description and argument types. The create_agent replaces the loop and messages list which lets us skip appending messages, the agent keeps the convo in its own state and loops between model and tools until a tool is not being called anymore. run_tool() is also gone and the agent finds each tool itself, MAX_ITERATIONS is gone but we have recursion_limit, if we dont define recursion limit then it would go to the default of 10,007 steps. 

### What did LangChain do that you did NOT have last week? Hint: make a tool raise an exception, and ask for a tool name that does not exist. Compare to your Week 1 crash.
For making a tool raise an exception, i put this line of code in the get_weather function "raise ConnectionError("weather service is down")" in both step c and step d. Both version crashed but the difference is that week1 code showed errors on run_tool, get_weather, and shows the exception error. Meanwhile, LangChain showed many lines of error about the librarys code. 
For asking a tool name that doesnt exist, i put the line "SYSTEM_PROMPT = "You are a helpful assistant. Answer clearly and concisely. You also have a tool called get_time(city) that returns the local time in a city."" at the beginning of both step c and d, and neither of them crashed. But the difference is that week1 showed its because of the else branch in run_tool (would fail if "else" branch wasnt there), but for LangChain it handled that code for me saying that get time is not a valid tool. LangChain adds built in handling for a nonexisting tool that I didnt have in week1. 


### One thing that was harder or more confusing in LangChain than in raw Python.
One thing that was harder is that that the exception error was like 100 lines rather than 3 that week1 faced where I could see each error in code, the debugging is harder on LangChain. Had to use middleware to print each tool call so i couldnt just add a print in a loop since there is none in LangChain, now its in create_agent as a graph. I also dont know what LangGraph is so that's also confusing on how that is linked to this.  

## Reflection

### Where did your Week 1 loop go? Point to the LangChain concept that owns each piece now.
1. Describing tools is before each tool function with @tool
2. Running the tool instead of run_tool is now in create_agent with the tools node below line 97
3. Instead of json.loads in line 129 of step c, we dont need to write that line because agent handles it. 
4. Checking for tool calls in step c with lines 121-124 to see if it should break if theres no tools being called, now create_agent handles it.
5. Doesnt have messages list, its part of agent state from lines 106-109 in step D. Final answer is on line 109 with result of messages. 
6. Uses middleware in step D line 68 for printing in a loop

### When would you NOT use LangChain for a project? Be specific.
I would not use LangChain if I dont need memory access and would like to debug easily with print statements without middleware. As I saw when doing question 3 of conversion notes, I saw that the traceback was 3 lines of my own code versus 100 lines of library code of LangChain to debug. 

i need to print and debug in a loop without middleware and dont need memory access, if i dont need the agent to remember employee emails/information. 