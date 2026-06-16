#!/usr/bin/env python3
# test_governed_agent.py
# End-to-end test cases that verify the MiniMax M2.5 + OpenBox + LangGraph
# integration works and that runs are captured in the OpenBox dashboard.
#
# Usage:
#   python test_governed_agent.py          # run all test cases
#   python test_governed_agent.py --quick  # skip the live LLM round-trip
#
# Each live test makes a small governed agent run so a corresponding audit
# trail / trace should appear in the OpenBox dashboard (https://platform.openbox.ai).

import os
import sys
import asyncio
import traceback
from dotenv import load_dotenv

load_dotenv()

PASS = "PASS"
FAIL = "FAIL"
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}" + (f" -> {detail}" if detail else ""))


# ── Test 1: agent graph imports & compiles ────────────────────────────────
def test_graph_compiles():
    print("\n[Test 1] LangGraph graph imports and compiles...")
    try:
        from agent import app
        assert app is not None, "compiled graph 'app' is None"
        record("graph_compiles", True, "agent.app compiled")
        return True
    except Exception as e:
        record("graph_compiles", False, str(e))
        traceback.print_exc()
        return False


# ── Test 2: tools are registered ──────────────────────────────────────────
def test_tools_registered():
    print("\n[Test 2] Agent tools are registered...")
    try:
        from agent import tools
        names = sorted(t.name for t in tools)
        expected = {"read_file", "write_file", "list_files",
                    "search_code", "run_python", "run_shell"}
        missing = expected - set(names)
        assert not missing, f"missing tools: {missing}"
        record("tools_registered", True, ", ".join(names))
        return True
    except Exception as e:
        record("tools_registered", False, str(e))
        return False


# ── Test 3: OpenBox governance wrapper builds ─────────────────────────────
def test_governance_wrapper():
    print("\n[Test 3] OpenBox governance wrapper builds around the graph...")
    try:
        from openbox_langgraph import create_openbox_graph_handler
        from agent import app
        governed = create_openbox_graph_handler(
            graph=app,
            api_url=os.getenv("OPENBOX_URL"),
            api_key=os.getenv("OPENBOX_API_KEY"),
            agent_did=os.getenv("OPENBOX_AGENT_DID"),
            agent_private_key=os.getenv("OPENBOX_AGENT_PRIVATE_KEY"),
            agent_name="MiniMax-Code-Agent-Test",
        )
        assert hasattr(governed, "ainvoke"), "governed handler missing ainvoke"
        record("governance_wrapper", True, "create_openbox_graph_handler ok")
        return governed
    except Exception as e:
        record("governance_wrapper", False, str(e))
        traceback.print_exc()
        return None


# ── Test 4: live governed run (captured in OpenBox dashboard) ─────────────
async def test_live_run(governed):
    print("\n[Test 4] Live governed agent run (check OpenBox dashboard)...")
    if governed is None:
        record("live_run", False, "skipped: no governed handler")
        return False
    try:
        result = await governed.ainvoke(
            {"messages": [("user", "Reply with exactly the word: PONG")]},
            config={"configurable": {"thread_id": "test-pong-001"}},
        )
        msgs = result.get("messages", [])
        final = ""
        for msg in reversed(msgs):
            if getattr(msg, "type", None) == "ai" and msg.content:
                final = msg.content
                break
        assert msgs, "no messages returned"
        record("live_run", True, f"agent replied: {final!r}")
        print("  -> A trace for thread 'test-pong-001' should now appear in OpenBox.")
        return True
    except Exception as e:
        record("live_run", False, str(e))
        traceback.print_exc()
        return False


# ── Test 5: live tool-using run (exercises governed tool calls) ───────────
async def test_live_tool_run(governed):
    print("\n[Test 5] Live tool-using run (fibonacci) ...")
    if governed is None:
        record("live_tool_run", False, "skipped: no governed handler")
        return False
    try:
        result = await governed.ainvoke(
            {"messages": [("user",
                "Use run_python to compute and print the 10th Fibonacci number.")]},
            config={"configurable": {"thread_id": "test-fib-001"}},
        )
        msgs = result.get("messages", [])
        assert msgs, "no messages returned"
        record("live_tool_run", True, f"{len(msgs)} messages in trace")
        print("  -> A trace for thread 'test-fib-001' should now appear in OpenBox.")
        return True
    except Exception as e:
        record("live_tool_run", False, str(e))
        traceback.print_exc()
        return False


def main():
    quick = "--quick" in sys.argv
    print("=" * 60)
    print("  MiniMax + OpenBox + LangGraph — Integration Test Cases")
    print("=" * 60)

    test_graph_compiles()
    test_tools_registered()
    governed = test_governance_wrapper()

    if not quick:
        asyncio.run(test_live_run(governed))
        asyncio.run(test_live_tool_run(governed))
    else:
        print("\n(--quick) Skipping live LLM round-trips.")

    print("\n" + "=" * 60)
    print("SUMMARY:")
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, _ in results:
        print(f"  {'PASS' if ok else 'FAIL'} : {name}")
    print("=" * 60)
    print(f"  {passed}/{len(results)} checks passed")
    if not quick:
        print("  View the audit trails at: https://platform.openbox.ai")
    print("=" * 60)

    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
