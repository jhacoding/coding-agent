We want to make a coding agent in python which can solve simple bugs. We will use groq llm for this.

The llm will have some tools which will help in solveing the bugs.
One tool can be search files which lists path of files which are related to the bug as per the llm.
We need search in file tool which can give line numbers related to the bug.
We need replace which allows the replacing a line with another line.

To test this, I want to test this myself. Prepare a simple .cpp file and write boilerplate code in it. Do not introduce any bug now, I will introduce the bug and test it myself.

I want to give the bug in simple english in cli and the llm and the tools should solve it.
Make the system without langgraph and keep it simple.

Also there will be max retry of 4 times. If the llm can't solve the bugs inside this limit, it should print a message saying that it cannot solve the bug.

Also there should be clear print statements saying which tool was called at each step.[We want to understand the flow completely. As soon as I change the cpp file and run the agent, it should ask me my bug. After I give my bug, it should begin solving it.]

Do not write any test cases for now.
If anything is unclear, ask me.