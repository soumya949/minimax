# Developer Notes — MiniMax + OpenBox Integration

## Current status
- **Goal:** Run a coding agent on **MiniMax M2.5** (via OpenRouter) under
  **OpenBox** governance, orchestrated with **LangGraph**. This is working.
- Every LLM call, tool call, and node transition is captured by OpenBox and is
  visible in the dashboard: https://platform.openbox.ai

## Files
- `agent.py` — LangGraph ReAct agent + tools + MiniMax M2.5 LLM config.
- `governed_agent.py` — wraps the compiled graph with OpenBox governance.
- `test_connections.py` — pre-flight credential / connectivity checks.
- `test_governed_agent.py` — integration test cases (compile, tools, governed runs).

## Model configuration (important)
- The free slug `minimax/minimax-m2.5:free` was **retired** by OpenRouter and
  now returns **404**. We use the standard slug `minimax/minimax-m2.5`.
- `max_tokens` is capped at **2048** in `agent.py`. The model otherwise defaults
  to 65536, which triggers an OpenRouter **402 "insufficient credits"** error on
  free/limited accounts.

---

## SIDE NOTE 1 — Future: switching to MiniMax M3
When M3 access becomes available:
1. In `agent.py`, change `model="minimax/minimax-m2.5"` to
   `model="minimax/minimax-m3"` (or `minimax/minimax-m3:free` if a free tier
   exists).
2. Also update the model slug in `test_connections.py` (the `test_openrouter`
   request body) so the pre-flight test points at M3.
3. Consider raising `max_tokens` if the account has enough credits / paid plan.
4. Re-run `python test_connections.py` then `python test_governed_agent.py`.

---

## SIDE NOTE 2 — For the Temporal developer
This implementation uses **LangGraph** for orchestration. A parallel
implementation using **Temporal** is planned. Key points to carry over:

- **Keep OpenBox governance.** The governance layer (DID + private key signing,
  risk scoring, audit trail) is independent of the orchestrator. Reuse the same
  OpenBox credentials from `.env`:
  - `OPENBOX_URL`, `OPENBOX_API_KEY`, `OPENBOX_AGENT_DID`, `OPENBOX_AGENT_PRIVATE_KEY`
- **Where governance hooks in:** In LangGraph we wrap the compiled graph with
  `create_openbox_graph_handler(...)`. In Temporal, the equivalent is to wrap
  each **Activity** (LLM call + each tool call) so every step is reported to
  OpenBox — i.e. governance must wrap the unit of work, not the workflow loop.
- **Reuse the tools** from `agent.py` (`read_file`, `write_file`, `list_files`,
  `search_code`, `run_python`, `run_shell`) as Temporal Activities. They are
  plain functions decorated with `@tool`; the underlying logic is portable.
- **Same model + token cap** apply (see model configuration above).
- **Determinism:** LLM/tool calls are non-deterministic, so they belong in
  Activities, not directly in the Workflow function.
- Verify Temporal runs also surface in the OpenBox dashboard the same way the
  LangGraph runs do.

---

## How to verify everything is wired up
```bash
pip install -r requirements.txt
python test_connections.py        # credentials + connectivity
python test_governed_agent.py     # integration tests + live governed runs
python test_governed_agent.py --quick   # skip live LLM calls (no credits used)
```
After the live tests, check https://platform.openbox.ai for the traces with
thread ids `test-pong-001` and `test-fib-001`.
