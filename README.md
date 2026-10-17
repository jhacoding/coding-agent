# Bug-Fixing Coding Agent

A small coding agent written in plain Python that fixes simple bugs in your code.
You describe the bug in simple English, and an LLM (running on [Groq](https://groq.com)) uses a few tools to find the buggy line and fix it. No agent frameworks (no LangGraph / LangChain) - just a readable loop, so you can follow every step.

Works on **C, C++, Java and Python** projects.

## How it works

```
 You describe the bug
        |
        v
 LLM calls tools: find the file -> find the lines -> read the code -> replace the line
        |
        v
 Syntax check (g++ / gcc / javac / Python compile)
        |
        v
 You test the program and confirm: "Is the bug fixed? [y/n]"
        |
        +-- yes --> done
        +-- no  --> feedback goes back to the LLM, next attempt (max 4)
```

If the bug is not fixed within **4 attempts**, the agent says it cannot solve it and restores your files to their original state.

Every step is printed (`[TOOL CALL]`, `[TOOL RESULT]`, `[CHECK]`, ...) so you can see exactly what the agent is doing.

## Tools the LLM can use

| Tool | What it does |
|------|--------------|
| `search_files(keyword)` | Lists code files related to the keyword(s) |
| `search_in_file(path, keyword)` | Returns matching line numbers with their content |
| `read_file(path, start_line, end_line)` | Shows numbered lines of a file for context |
| `replace_line(path, line_number, new_line)` | Replaces one line with another line |

All file access is limited to the project folder you point the agent at.

## Setup

You need Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <your-repo-url>
cd <your-repo-name>
uv sync
```

Get a free API key from [console.groq.com/keys](https://console.groq.com/keys) and create a `.env` file next to `agent.py`:

```
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

`.env` is listed in `.gitignore`, so your key is never pushed to GitHub.

Optional, for the syntax check: `g++`/`gcc` for C/C++ and a JDK (`javac`) for Java. If a compiler is missing, that check is skipped.

## Usage

Sample programs (all bug-free) are in the `samples/` folder:

```
samples/
  main.c
  main.cpp
  Main.java
  sample.py
```

1. Introduce a bug in a sample file and **save** it. For example, in `samples/main.cpp` change `i <= n` to `i < n` in `factorial`.
2. Run the agent on that file:

```bash
uv run agent.py --dir samples/main.cpp
```

`--dir` accepts a **single code file** (the agent works on that file only) or a **folder** (it scans every supported file inside). The same works for the other samples:

```bash
uv run agent.py --dir samples/main.c
uv run agent.py --dir samples/Main.java
uv run agent.py --dir samples/sample.py
```

Tip: use one file per run. Pointing the agent at the whole `samples` folder lets it see all four languages at once, which can confuse it when they share function names.

3. When asked, describe the bug: `factorial(5) prints 24 instead of 120`
4. Watch the agent work, then test your program and answer `y` or `n`.

Run commands for each sample (run them inside the `samples` folder):

| Language | Build and run |
|----------|---------------|
| C | `gcc main.c -o main && ./main` |
| C++ | `g++ -std=c++17 main.cpp -o main && ./main` |
| Java | `javac Main.java && java Main` (the file must be named `Main.java`) |
| Python | `python sample.py` |

## Configuration

| Setting | Where | Default |
|---------|-------|---------|
| `GROQ_MODEL` | `.env` | `openai/gpt-oss-120b` |
| `MAX_RETRIES` (fix attempts) | top of `agent.py` | 4 |
| `MAX_STEPS_PER_ATTEMPT` (tool calls per attempt) | top of `agent.py` | 10 |
| `MAX_API_RETRIES` (rate limits / bad tool calls) | top of `agent.py` | 3 |

If your Groq account cannot use a model, pick another tool-calling model from the list your key has access to.

## Built-in safeguards

- Blocks repeated identical tool calls so the LLM does not loop.
- Retries automatically on Groq rate limits and malformed tool calls (these do not use up a fix attempt).
- Fails fast with a clear message if the folder is missing or has no code files.
- Restores the original files if all attempts fail.
- Never edits its own script.

## Limitations

- `replace_line` swaps one line for one line, so it cannot insert or delete lines.
- Search is keyword based, not semantic.
- The automatic check is a syntax/compile check only. Logic bugs are confirmed by you at the final `y/n` question.
- Meant for small, simple bugs in small projects.

## Project structure

```
agent.py          the agent (tools, LLM loop, checks)
samples/          bug-free sample programs in C, C++, Java, Python
pyproject.toml    dependencies (groq, python-dotenv)
.env              your API key (not committed)
```