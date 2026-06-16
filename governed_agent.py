# governed_agent.py
# OpenBox wraps the LangGraph agent — every tool call, LLM call,
# and node transition is captured, risk-scored, and auditable.

import os
import asyncio
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

from dotenv import load_dotenv
from openbox_langgraph import create_openbox_graph_handler

from agent import app  # the compiled LangGraph graph

load_dotenv()

# ── Wrap the compiled graph with OpenBox governance ───────────────────────
governed = create_openbox_graph_handler(
    graph=app,
    api_url=os.getenv("OPENBOX_URL"),
    api_key=os.getenv("OPENBOX_API_KEY"),
    agent_did=os.getenv("OPENBOX_AGENT_DID"),
    agent_private_key=os.getenv("OPENBOX_AGENT_PRIVATE_KEY"),
    agent_name="MiniMax-Code-Agent",
)

def _normalize_messages(messages: Iterable[Any]) -> List[Tuple[str, str]]:
    """Convert an iterable of tuples/dicts into LangGraph message tuples."""

    normalized: List[Tuple[str, str]] = []
    for msg in messages:
        role: str
        content: str

        if isinstance(msg, tuple) and len(msg) == 2:
            role, content = msg  # type: ignore[misc]
        elif isinstance(msg, Mapping):
            role = msg.get("role")  # type: ignore[assignment]
            content = msg.get("content")  # type: ignore[assignment]
        else:
            raise TypeError(
                "Each message must be a (role, content) tuple or mapping with role/content keys"
            )

        if role is None or content is None:
            raise ValueError("Message entries require non-empty 'role' and 'content'")

        normalized.append((str(role), str(content)))

    if not normalized:
        raise ValueError("At least one message is required for agent invocation")

    return normalized


def _merge_configurations(
    session_id: str,
    overrides: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    base: Dict[str, Any] = {"configurable": {"thread_id": session_id}}
    if not overrides:
        return base

    merged = dict(base)
    for key, value in overrides.items():
        if key == "configurable" and isinstance(value, MutableMapping):
            merged.setdefault("configurable", {}).update(value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


def _extract_final_ai_message(result: Mapping[str, Any]) -> str | None:
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "type") and getattr(msg, "type") == "ai" and getattr(msg, "content", None):
            return getattr(msg, "content")
    return None


# ── Reusable governed invocation helper ───────────────────────────────────
async def invoke_agent(
    messages: Sequence[Any],
    session_id: str = "session-001",
    *,
    config_overrides: Mapping[str, Any] | None = None,
) -> Tuple[str | None, Mapping[str, Any]]:
    """Invoke the governed LangGraph agent with arbitrary message history."""

    normalized = _normalize_messages(messages)

    try:
        config = _merge_configurations(session_id, config_overrides)
        result = await governed.ainvoke({"messages": normalized}, config=config)
    except Exception as e:
        raise RuntimeError(
            f"Governed agent invocation failed for session '{session_id}': {e}"
        ) from e

    final = _extract_final_ai_message(result)
    return final, result


# ── Run a single governed session (console helper) ─────────────────────────
async def run(user_message: str, session_id: str = "session-001"):
    print(f"\n{'='*60}")
    print(f"[User]: {user_message}")
    print(f"{'='*60}\n")

    try:
        final, result = await invoke_agent([("user", user_message)], session_id=session_id)
    except Exception as e:
        print(f"[OpenBox/Agent Error]: {type(e).__name__}: {e}")
        print(f"\n{'='*60}")
        print("✗ Session stopped. Check OpenBox dashboard for policy evaluation:")
        print("  https://platform.openbox.ai")
        print(f"{'='*60}\n")
        raise

    if final:
        print(f"[Agent]: {final}")

    print(f"\n{'='*60}")
    print("✓ Session complete. Check OpenBox dashboard for full audit trail:")
    print("  https://platform.openbox.ai")
    print(f"{'='*60}\n")

    return result


# ── Streaming version (token-by-token output) ─────────────────────────────
async def run_streaming(user_message: str, session_id: str = "session-002"):
    print(f"\n{'='*60}")
    print(f"[User]: {user_message}")
    print(f"{'='*60}\n[Agent]: ", end="", flush=True)

    normalized = _normalize_messages([("user", user_message)])

    async for chunk in governed.astream_governed(
        {"messages": normalized},
        stream_mode="values",
    ):
        msgs = chunk.get("messages", [])
        if msgs:
            last = msgs[-1]
            if hasattr(last, "type") and last.type == "ai" and last.content:
                print(last.content, end="", flush=True)

    print(f"\n\n{'='*60}")
    print("✓ Streamed session complete. View at https://platform.openbox.ai")
    print(f"{'='*60}\n")


# ── Entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # Default demo task
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "List files in current directory, then create a file called "
        "hello_minimax.py that prints 'Hello from MiniMax M2.5 + OpenBox!', "
        "then run it and show me the output."
    )

    asyncio.run(run(task, session_id="demo-001"))
