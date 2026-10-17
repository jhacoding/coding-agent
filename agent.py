#!/usr/bin/env python3
"""
A tiny bug-fixing coding agent.

- LLM: Groq (OpenAI-style tool calling)
- No frameworks (no langgraph / langchain) - just a plain loop.

Tools the LLM can call:
    search_files(keyword)                    -> list code files related to the keyword(s)
    search_in_file(path, keyword)            -> line numbers (+ content) matching the keyword(s)
    read_file(path, start_line, end_line)    -> numbered lines of a file (to see context)
    replace_line(path, line_number, new_line)-> replace exactly one line with another line

Flow:
    1. Ask the user to describe the bug (plain English).
    2. Attempt loop (max 4 attempts):
         a. LLM uses tools to find and fix the bug.
         b. We syntax-check the C++ files with g++ (if installed).
         c. We ask the user whether the bug is really fixed.
         d. If not, the reason is fed back to the LLM and the next attempt starts.
    3. If all attempts are used, print that we could not solve it and restore the files.

Usage:
    export GROQ_API_KEY=...        (Windows PowerShell: $env:GROQ_API_KEY="...")
    python agent.py                (works on the current directory)
    python agent.py --dir samples/java      (c, cpp, java, python ...)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv()   # reads GROQ_API_KEY (and optionally GROQ_MODEL) from a .env file

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
MAX_RETRIES = 4                 # max number of fix attempts
MAX_STEPS_PER_ATTEMPT = 10      # max tool-calling rounds inside a single attempt
MAX_API_RETRIES = 3             # re-tries for rate limits / malformed tool calls (do NOT use up an attempt)
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
CODE_EXTS = {".cpp", ".cc", ".c", ".h", ".hpp", ".java", ".py"}
SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules", ".idea", ".vscode"}
MAX_PREVIEW_LINES = 12          # how many lines of a tool result we echo to the terminal


# ----------------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------------
class Tools:
    """The functions the LLM can call. All paths are relative to the project root."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.self_path = Path(__file__).resolve()   # never let the LLM edit the agent itself
        self.originals = {}          # rel_path -> original text (for restoring on failure)
        self.change_log = []         # human-readable list of every edit made
        self.edits_in_attempt = 0

    # ---- helpers -----------------------------------------------------------
    def _rel(self, p: Path) -> str:
        return str(p.relative_to(self.root)).replace("\\", "/")

    def _resolve(self, path: str) -> Path:
        p = (self.root / path).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError(f"'{path}' is outside the project directory.")
        if not p.is_file():
            raise FileNotFoundError(f"File not found: '{path}'. Use search_files to list files.")
        return p

    def code_files(self):
        found = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix.lower() in CODE_EXTS and p.resolve() != self.self_path:
                    found.append(p)
        return sorted(found)

    @staticmethod
    def _terms(keyword: str):
        return [t for t in str(keyword).lower().replace(",", " ").split() if t]

    # ---- tool 1: search_files ---------------------------------------------
    def search_files(self, keyword: str = "") -> str:
        terms = self._terms(keyword)
        matches = []
        for f in self.code_files():
            rel = self._rel(f)
            if not terms:
                matches.append(rel)
                continue
            text = f.read_text(errors="ignore").lower()
            if any(t in rel.lower() or t in text for t in terms):
                matches.append(rel)
        if not matches:
            return "No matching files found. Try different keywords, or an empty keyword to list all files."
        return "\n".join(matches)

    # ---- tool 2: search_in_file -------------------------------------------
    def search_in_file(self, path: str, keyword: str) -> str:
        p = self._resolve(path)
        terms = self._terms(keyword)
        if not terms:
            return "ERROR: keyword is empty."
        lines = p.read_text(errors="ignore").splitlines()
        hits = []
        for i, line in enumerate(lines, start=1):
            low = line.lower()
            if any(t in low for t in terms):
                hits.append(f"{i}: {line}")
        if not hits:
            return f"No lines matching '{keyword}' in {path} (file has {len(lines)} lines)."
        return f"(file has {len(lines)} lines)\n" + "\n".join(hits[:30])

    # ---- extra helper tool: read_file -------------------------------------
    def read_file(self, path: str, start_line: int = 1, end_line: int = 0) -> str:
        p = self._resolve(path)
        lines = p.read_text(errors="ignore").splitlines()
        start = max(1, int(start_line))
        end = int(end_line) if int(end_line) > 0 else len(lines)
        end = min(end, len(lines), start + 119)   # cap at 120 lines per call
        if start > len(lines):
            return f"ERROR: start_line {start} is beyond the end of the file ({len(lines)} lines)."
        out = [f"{i}: {lines[i - 1]}" for i in range(start, end + 1)]
        return f"(showing lines {start}-{end} of {len(lines)})\n" + "\n".join(out)

    # ---- tool 3: replace_line ---------------------------------------------
    def replace_line(self, path: str, line_number: int, new_line: str) -> str:
        p = self._resolve(path)
        rel = self._rel(p)
        line_number = int(line_number)
        new_line = str(new_line)
        if "\n" in new_line or "\r" in new_line:
            return "ERROR: new_line must be a single line (no newline characters)."

        text = p.read_text()
        had_trailing_newline = text.endswith("\n")
        lines = text.split("\n")
        if had_trailing_newline:
            lines = lines[:-1]

        if line_number < 1 or line_number > len(lines):
            return f"ERROR: line_number {line_number} is out of range (file has {len(lines)} lines)."

        if rel not in self.originals:
            self.originals[rel] = text   # remember the very first version

        old_line = lines[line_number - 1]
        lines[line_number - 1] = new_line
        p.write_text("\n".join(lines) + ("\n" if had_trailing_newline else ""))

        self.edits_in_attempt += 1
        self.change_log.append(f"{rel}:{line_number}\n      - {old_line}\n      + {new_line}")
        return (f"OK. Replaced line {line_number} of {rel}.\n"
                f"- {old_line}\n"
                f"+ {new_line}")

    def restore_originals(self):
        for rel, text in self.originals.items():
            (self.root / rel).write_text(text)

    # ---- dispatcher --------------------------------------------------------
    def call(self, name: str, args: dict) -> str:
        funcs = {
            "search_files": self.search_files,
            "search_in_file": self.search_in_file,
            "read_file": self.read_file,
            "replace_line": self.replace_line,
        }
        if name not in funcs:
            return f"ERROR: unknown tool '{name}'."
        try:
            return funcs[name](**args)
        except Exception as e:  # return the error to the LLM so it can correct itself
            return f"ERROR: {type(e).__name__}: {e}"


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": ("List project code files that are related to the given keyword(s). "
                            "Matches on file name or file content. Use an empty keyword to list all files."),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "One or more space-separated keywords."}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": ("Search a file for keyword(s) and return the matching line numbers with their content. "
                            "Line numbers are 1-based."),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to the project root."},
                    "keyword": {"type": "string", "description": "One or more space-separated keywords."},
                },
                "required": ["path", "keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a range of lines from a file, with line numbers. Use it to see the context around a suspicious line.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "description": "First line to show (1-based). Default 1."},
                    "end_line": {"type": "integer", "description": "Last line to show. 0 or omitted = end of file."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_line",
            "description": ("Replace exactly ONE line of a file with a new single line. The new line must include its own "
                            "indentation. The total number of lines never changes, so other line numbers stay valid."),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "line_number": {"type": "integer", "description": "1-based line number to replace."},
                    "new_line": {"type": "string", "description": "The full replacement line (single line, with indentation)."},
                },
                "required": ["path", "line_number", "new_line"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a careful coding agent that fixes simple bugs in a small C, C++, Java or Python project.

You are given a bug description in plain English. You can use these tools:
  - search_files(keyword): find files related to the bug
  - search_in_file(path, keyword): find line numbers related to the bug
  - read_file(path, start_line, end_line): read lines with line numbers for context
  - replace_line(path, line_number, new_line): replace ONE line with ONE new line

Workflow:
  1. Use search_files to find the relevant file(s).
  2. Use search_in_file and/or read_file to locate the buggy line(s). Always look at the code before editing.
  3. Use replace_line to fix the bug. Keep the original indentation and style. Make the smallest change that fixes the bug.
  4. When the fix is done, reply with a short plain-text summary (no tool call) of what you changed and why.

Rules:
  - replace_line swaps one line for one line, so line numbers never shift. If you need several statements, put them on one line.
  - Never guess line numbers. Verify them with search_in_file / read_file first.
  - Do not change code that is unrelated to the bug.
  - Do NOT repeat a tool call you already made - the result will be the same. Move forward instead.
  - Prefer search_in_file to locate a function, then read_file for just that function (10-30 lines). Do not read whole files.
  - If you have read the relevant code and it already looks correct (it does not match the bug report), do NOT edit
    anything. Reply with a short explanation, quoting the exact line(s) you checked, so the user can double-check
    the report.
  - If you are told a previous fix was rejected, re-read the current code (it may already contain your earlier edits) and try a different approach.
"""


# ----------------------------------------------------------------------------
# Helpers for printing / verification
# ----------------------------------------------------------------------------
def preview(text: str, limit: int = MAX_PREVIEW_LINES) -> str:
    lines = text.splitlines()
    shown = lines[:limit]
    if len(lines) > limit:
        shown.append(f"... ({len(lines) - limit} more lines - not shown here, but the LLM receives the full result)")
    return "\n".join("        " + l for l in shown)


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def syntax_check(tools: Tools):
    """Language-aware check of all code files. Returns (ok, output)."""
    files = tools.code_files()
    by_ext = {}
    for f in files:
        by_ext.setdefault(f.suffix.lower(), []).append(f)
    problems = []

    # C
    c_files = by_ext.get(".c", [])
    cc = shutil.which("gcc") or shutil.which("clang")
    for src in c_files:
        if not cc:
            print("  [CHECK] gcc/clang not found - skipping C check.")
            break
        rel = tools._rel(src)
        print(f"  [CHECK] {Path(cc).name} -fsyntax-only {rel}")
        r = _run([cc, "-Wall", "-fsyntax-only", str(src)])
        if r.returncode != 0:
            problems.append(f"{rel}:\n{r.stderr.strip()}")

    # C++
    cpp_files = by_ext.get(".cpp", []) + by_ext.get(".cc", [])
    cxx = shutil.which("g++") or shutil.which("clang++")
    for src in cpp_files:
        if not cxx:
            print("  [CHECK] g++/clang++ not found - skipping C++ check.")
            break
        rel = tools._rel(src)
        print(f"  [CHECK] {Path(cxx).name} -std=c++17 -fsyntax-only {rel}")
        r = _run([cxx, "-std=c++17", "-Wall", "-fsyntax-only", str(src)])
        if r.returncode != 0:
            problems.append(f"{rel}:\n{r.stderr.strip()}")

    # Java (compile everything together into a temp dir, nothing is left behind)
    java_files = by_ext.get(".java", [])
    if java_files:
        javac = shutil.which("javac")
        if not javac:
            print("  [CHECK] javac not found - skipping Java check.")
        else:
            rels = [tools._rel(f) for f in java_files]
            print(f"  [CHECK] javac {' '.join(rels)}")
            with tempfile.TemporaryDirectory() as tmp:
                r = _run([javac, "-d", tmp] + [str(f) for f in java_files])
            if r.returncode != 0:
                problems.append("Java:\n" + r.stderr.strip())

    # Python (pure syntax check, the code is NOT executed)
    for src in by_ext.get(".py", []):
        rel = tools._rel(src)
        print(f"  [CHECK] python syntax check {rel}")
        try:
            compile(src.read_text(), str(src), "exec")
        except SyntaxError as e:
            problems.append(f"{rel}:\nSyntaxError: {e.msg} (line {e.lineno})")

    if not files:
        print("  [CHECK] No code files found to check.")
    if problems:
        return False, "\n\n".join(problems)
    print("  [CHECK] Syntax check passed.")
    return True, ""


RUN_HINTS = {
    ".c": "gcc main.c -o main && ./main",
    ".cpp": "g++ -std=c++17 main.cpp -o main && ./main",
    ".java": "javac Main.java && java Main",
    ".py": "python sample.py",
}


# ----------------------------------------------------------------------------
# One attempt = a loop of LLM -> tool calls -> LLM ... until the LLM stops calling tools
# ----------------------------------------------------------------------------
def parse_wait_seconds(text: str) -> float:
    """Read 'Please try again in 405ms' / '1m2.5s' out of a Groq rate-limit message."""
    m = re.search(r"try again in\s+((?:\d+(?:\.\d+)?(?:ms|m|s))+)", text)
    if not m:
        return 5.0
    total = 0.0
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)(ms|m|s)", m.group(1)):
        total += float(num) * {"ms": 0.001, "s": 1, "m": 60}[unit]
    return min(total + 0.5, 60.0)


def call_llm(client: Groq, messages: list):
    """One LLM call. Retries rate limits and malformed tool calls. Returns (response, error_text)."""
    last_err = ""
    for retry in range(MAX_API_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0 if retry == 0 else 0.4,   # tiny randomness on a retry avoids the same bad output
            )
            return resp, None
        except Exception as e:
            text = str(e)
            last_err = text
            if any(k in text for k in ("model_not_found", "invalid_api_key", "401")):
                print(f"  [ERROR] Groq API call failed: {text}")
                print("  [AGENT] This is a setup problem (model/API key), not a bug-fixing failure. Exiting.")
                sys.exit(1)
            if retry == MAX_API_RETRIES:
                break
            if "rate_limit_exceeded" in text or "429" in text:
                wait = parse_wait_seconds(text)
                print(f"  [AGENT] Groq rate limit hit. Waiting {wait:.1f}s, then retrying "
                      f"({retry + 1}/{MAX_API_RETRIES})...")
                time.sleep(wait)
            elif "tool_use_failed" in text:
                print(f"  [AGENT] The model produced a malformed tool call. Retrying this step "
                      f"({retry + 1}/{MAX_API_RETRIES})...")
            else:
                print(f"  [ERROR] Groq API call failed: {text}")
                return None, f"The LLM API call failed: {text}"
    print(f"  [ERROR] Groq API kept failing: {last_err}")
    return None, f"The LLM API kept failing: {last_err}"


# ----------------------------------------------------------------------------
# One attempt = a loop of LLM -> tool calls -> LLM ... until the LLM stops calling tools
# ----------------------------------------------------------------------------
def run_attempt(client: Groq, messages: list, tools: Tools, attempt: int):
    """Returns (error, final_text). error is None if the LLM finished normally."""
    tools.edits_in_attempt = 0
    seen_calls = set()      # (tool, args) already made since the last edit
    duplicates = 0

    for step in range(1, MAX_STEPS_PER_ATTEMPT + 1):
        print(f"\n  --- Step {step} (attempt {attempt}/{MAX_RETRIES}): asking the LLM what to do next ---")
        resp, api_error = call_llm(client, messages)
        if api_error:
            return api_error, ""

        msg = resp.choices[0].message

        # No tool calls -> the LLM considers its work finished.
        if not msg.tool_calls:
            text = (msg.content or "").strip()
            messages.append({"role": "assistant", "content": text})
            print("  [LLM] Finished (no more tool calls). Its summary:")
            print(preview(text, 20) if text else "        (empty)")
            return None, text

        if msg.content and msg.content.strip():
            print(f"  [LLM] {msg.content.strip()}")

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = None

            if args is None:
                result = "ERROR: tool arguments were not valid JSON."
                print(f"  [TOOL CALL] {name}  (invalid JSON arguments)")
            else:
                arg_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
                key = name + json.dumps(args, sort_keys=True)
                if key in seen_calls:
                    duplicates += 1
                    print(f"  [TOOL CALL] {name}({arg_str})  <- repeated call, not executed again")
                    result = ("NOTE: you already made this exact call and nothing has changed since, so the "
                              "result would be identical. Do not repeat it. Either fix the bug with replace_line, "
                              "or - if the code is already correct - give your final answer explaining that.")
                else:
                    print(f"  [TOOL CALL] {name}({arg_str})")
                    edits_before = tools.edits_in_attempt
                    result = tools.call(name, args)
                    seen_calls.add(key)
                    if tools.edits_in_attempt != edits_before:
                        seen_calls.clear()      # files changed, earlier results are stale

            print("  [TOOL RESULT]")
            print(preview(result))
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        if duplicates >= 3:
            return ("You kept repeating the same tool calls instead of deciding what to do. "
                    "Either fix the bug, or say clearly that the code looks correct."), ""

    return f"You used all {MAX_STEPS_PER_ATTEMPT} tool steps without finishing.", ""


def build_messages(bug: str, notes: list, tools: Tools) -> list:
    """Fresh, compact conversation for each attempt (keeps token usage low)."""
    content = f"Bug report: {bug}"
    if notes:
        content += "\n\nPrevious attempts FAILED (do not just repeat them):\n"
        content += "\n".join(f"- Attempt {i}: {n}" for i, n in enumerate(notes, start=1))
    if tools.change_log:
        content += ("\n\nEdits already applied to the files (they are in the files NOW - re-read the code "
                    "before changing anything):\n" + "\n".join(f"  {c}" for c in tools.change_log))
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}]


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Simple bug-fixing agent (Groq).")
    parser.add_argument("--dir", default=".", help="Project directory (default: current directory)")
    args = parser.parse_args()

    if not os.environ.get("GROQ_API_KEY"):
        print("GROQ_API_KEY is not set.\n"
              "  Linux/macOS : export GROQ_API_KEY=your_key\n"
              "  PowerShell  : $env:GROQ_API_KEY=\"your_key\"")
        sys.exit(1)

    root = Path(args.dir).resolve()
    tools = Tools(root)
    client = Groq()

    print("=" * 70)
    print(" Bug-fixing agent")
    print(f" Model   : {MODEL}")
    print(f" Project : {root}")
    print(f" Max attempts: {MAX_RETRIES}")
    print("=" * 70)

    bug = input("\nDescribe the bug in simple English:\n> ").strip()
    if not bug:
        print("No bug description given. Exiting.")
        return

    notes = []              # one short line per failed attempt, passed to the next attempt
    last_llm_text = ""

    for attempt in range(1, MAX_RETRIES + 1):
        print("\n" + "=" * 70)
        print(f" ATTEMPT {attempt}/{MAX_RETRIES}")
        print("=" * 70)

        messages = build_messages(bug, notes, tools)

        # (a) let the LLM investigate and edit
        error, llm_text = run_attempt(client, messages, tools, attempt)
        if llm_text:
            last_llm_text = llm_text

        if error is None and tools.edits_in_attempt == 0:
            error = ("You finished without making any edit, so nothing was fixed. "
                     "Locate the buggy line and fix it with replace_line. "
                     "If you are sure the code is correct, say exactly which line you checked and why.")
            print(f"\n  [AGENT] The LLM made no edit - it did not find a bug that matches your description.")

        # (b) syntax check
        if error is None:
            print("\n  [AGENT] The LLM made edits. Verifying...")
            ok, output = syntax_check(tools)
            if not ok:
                print("  [CHECK] Compile errors:")
                print(preview(output, 20))
                error = "The code no longer compiles after your edits. Compiler output:\n" + output

        # (c) ask the user
        if error is None:
            print("\n  Changes made so far:")
            for entry in tools.change_log:
                print(f"    {entry}")
            print("\n  Please build and run your program to check the fix, e.g.:")
            present = sorted({f.suffix.lower() for f in tools.code_files()})
            for ext in present:
                if ext in RUN_HINTS:
                    print(f"      {RUN_HINTS[ext]}")
            answer = input("\n  Is the bug fixed? [y/n]: ").strip().lower()
            if answer.startswith("y"):
                print("\n" + "=" * 70)
                print(f" Bug fixed in attempt {attempt}/{MAX_RETRIES}.")
                print("=" * 70)
                return
            note = input("  What is still wrong? (press Enter to skip): ").strip()
            error = "The user tested your fix and says the bug is NOT fixed."
            if note:
                error += f" User feedback: {note}"

        # (d) remember why this attempt failed and retry
        print(f"\n  [AGENT] Attempt {attempt} did not solve the bug.")
        notes.append(error[:600])
        if attempt < MAX_RETRIES:
            print("  [AGENT] Starting a fresh attempt with feedback from this one...")

    # all attempts used
    print("\n" + "=" * 70)
    print(f" Sorry, I could not solve the bug within {MAX_RETRIES} attempts.")
    if last_llm_text:
        print("\n The LLM's last explanation was:")
        print(preview(last_llm_text, 15).replace("        ", "   ", 1))
    print("\n Tip: make sure your edit is SAVED in the file and that the bug description matches the code.")
    if tools.originals:
        tools.restore_originals()
        print(" All files have been restored to their original state.")
    print("=" * 70)


if __name__ == "__main__":
    main()