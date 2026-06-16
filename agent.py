# agent.py
# LangGraph ReAct agent powered by MiniMax M2.5 (free via OpenRouter)
# Tools: file read/write, code search, python execution, shell

import os
import subprocess
import tempfile
import time
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from minimax_media import generate_video, text_to_speech

load_dotenv()

# ── MiniMax M2.5 via OpenRouter ──────────────────────────────────────────
# NOTE: "minimax/minimax-m2.5:free" was retired by OpenRouter (now returns 404).
#       We use the standard "minimax/minimax-m2.5" slug.
# FUTURE (M3 access): when MiniMax M3 becomes available, change the model
#       slug below to "minimax/minimax-m3" (or "minimax/minimax-m3:free" if a
#       free tier is offered) and raise max_tokens. See NOTES.md.
llm = ChatOpenAI(
    model="minimax/minimax-m2.5",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "MiniMax-OpenBox-Agent",
    },
    temperature=0.3,
    # Capped to stay within OpenRouter free/limited credit balance.
    # The model defaults to 65536 which triggers a 402 "insufficient credits"
    # error on free accounts. Raise this once on a paid plan / M3 access.
    max_tokens=2048,
)

# ── Coding Agent Tools ────────────────────────────────────────────────────

@tool
def read_file(path: str) -> str:
    """Read the contents of a file. Returns the file text or an error message."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found at '{path}'"
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✓ Successfully wrote {len(content)} chars to '{path}'"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def list_files(directory: str = ".") -> str:
    """List all files recursively in a directory (skips hidden folders)."""
    try:
        files = []
        for root, dirs, filenames in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for filename in filenames:
                if not filename.startswith("."):
                    rel_path = os.path.relpath(os.path.join(root, filename), directory)
                    files.append(rel_path)
        return "\n".join(sorted(files)) if files else "No files found"
    except Exception as e:
        return f"Error listing files: {e}"


@tool
def search_code(query: str, directory: str = ".", file_extension: str = "py") -> str:
    """Search for a string pattern in code files. Returns matching lines with filenames."""
    try:
        result = subprocess.run(
            ["grep", "-r", f"--include=*.{file_extension}", "-n", "--color=never", query, directory],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip()
        return output if output else f"No matches for '{query}' in *.{file_extension} files"
    except FileNotFoundError:
        # grep not available, fallback
        import glob
        matches = []
        for filepath in glob.glob(f"{directory}/**/*.{file_extension}", recursive=True):
            try:
                with open(filepath) as f:
                    for i, line in enumerate(f, 1):
                        if query in line:
                            matches.append(f"{filepath}:{i}: {line.rstrip()}")
            except Exception:
                pass
        return "\n".join(matches) if matches else f"No matches for '{query}'"
    except Exception as e:
        return f"Error searching: {e}"


@tool
def run_python(code: str) -> str:
    """Execute a Python code snippet in a subprocess. Returns stdout and stderr."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True, text=True, timeout=30
        )
        os.unlink(tmp_path)
        output = result.stdout or ""
        if result.returncode != 0 and result.stderr:
            output += f"\n[stderr]:\n{result.stderr}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out (30s limit)"
    except Exception as e:
        return f"Error: {e}"


@tool
def run_shell(command: str) -> str:
    """Run a safe shell command (ls, cat, echo, pip, etc). Timeout: 15s."""
    # Basic safety: block destructive commands
    blocked = ["rm -rf", "sudo", "mkfs", "dd if=", "> /dev/", "chmod 777"]
    for b in blocked:
        if b in command:
            return f"Blocked: '{b}' is not allowed for safety reasons"
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=15
        )
        output = result.stdout or ""
        if result.returncode != 0 and result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (15s limit)"
    except Exception as e:
        return f"Error: {e}"


@tool
async def generate_speech(text: str, voice_id: str = "English_expressive_narrator") -> str:
    """Generate an MP3 speech file from text using MiniMax Text-to-Speech.
    Saves the audio next to the project and returns the saved file path."""
    try:
        audio_bytes = await text_to_speech(text, voice_id=voice_id)
        filename = f"speech_{int(time.time())}.mp3"
        out_path = os.path.abspath(os.path.join("generated_media", filename))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
        return f"✓ Audio generated ({len(audio_bytes)} bytes) saved to '{out_path}'"
    except Exception as e:
        return f"Error generating speech: {e}"


@tool
async def create_video(prompt: str, duration: int = 6, resolution: str = "768P") -> str:
    """Generate a short video from a text prompt using MiniMax video models.
    Returns a download URL for the generated MP4 (may take several minutes)."""
    try:
        url = await generate_video(prompt, duration=duration, resolution=resolution)
        return f"✓ Video generated. Download URL: {url}"
    except Exception as e:
        return f"Error generating video: {e}"


# ── Build LangGraph ReAct Graph ───────────────────────────────────────────

tools = [
    read_file,
    write_file,
    list_files,
    search_code,
    run_python,
    run_shell,
    generate_speech,
    create_video,
]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)


def call_model(state: MessagesState):
    """Agent node: call MiniMax with current messages."""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: MessagesState):
    """Route: use tools if the model made tool calls, else finish."""
    last = state["messages"][-1]
    return "tools" if last.tool_calls else END


graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

# This is the compiled graph — governed_agent.py wraps this with OpenBox
app = graph.compile()
