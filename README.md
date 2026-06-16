# MiniMax + LangGraph + OpenBox Agent

Governed coding agent: **MiniMax M2.5** (free via OpenRouter) + **LangGraph** orchestration + **OpenBox** governance.

## Architecture

```
User Prompt
    ↓
LangGraph ReAct Loop  ←→  MiniMax M2.5 (free, via OpenRouter)
    ↓                          ↓
  Tools:                  reasoning +
  read_file               tool selection
  write_file
  list_files
  search_code
  run_python
  run_shell
    ↓
OpenBox SDK (wraps the entire graph)
    ↓
OpenBox Dashboard → audit trail, risk score, session replay
```

## Setup

### 1. Fix your OpenRouter key

Your current key has a **domain allowlist restriction** which blocks it.

1. Go to https://openrouter.ai/settings/keys
2. **Revoke** the old key
3. Create a **new key** — leave the "Allowed Origins" field **blank**
4. Paste the new key into `.env`

### 2. Install dependencies

```bash
pip install langgraph langchain-openai openbox-langgraph-sdk-python python-dotenv
```

### 3. Configure `.env`

Copy `.env.example` to `.env`, then replace each placeholder with your own credentials. Do not commit `.env`.

```bash
# .env
OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY_HERE

OPENBOX_URL=https://core.openbox.ai
OPENBOX_API_KEY=YOUR_OPENBOX_API_KEY_HERE
OPENBOX_AGENT_DID=did:aip:YOUR_AGENT_DID_HERE
OPENBOX_AGENT_PRIVATE_KEY=YOUR_OPENBOX_AGENT_PRIVATE_KEY_HERE

MINIMAX_API_KEY=YOUR_MINIMAX_PLATFORM_KEY_HERE
MINIMAX_API_HOST=https://api.minimax.io
```

### 4. Test connections first

```bash
python test_connections.py
```

Expected output:
```
✓ OPENROUTER_API_KEY = sk-or-v1-xxxx...
✓ MiniMax M2.5 responded: 'CONNECTED'
✓ openbox_langgraph imported successfully
✅ All checks passed! Run: python governed_agent.py
```

### 5. Run the governed agent

```bash
# Default demo task
python governed_agent.py

# Custom task
python governed_agent.py "Write a Python script that sorts a list of numbers"
```

### 6. Launch the local chat experience

```bash
# Start the FastAPI server (serves REST API + chat UI)
uvicorn server:app --host 127.0.0.1 --port 8000

# Or
python server.py  # same as above, defaults to port 8000

# Visit the chat UI:
# http://127.0.0.1:8000/
```

What happens:

1. The browser chat UI (Space Grotesk theme) mirrors ChatGPT/Gemini style.
2. Each user turn calls `POST /api/chat` with the running conversation.
3. The FastAPI layer forwards the full history to `invoke_agent(...)` in `governed_agent.py`.
4. OpenBox governance continues to wrap every tool + LLM call; audit trails show up per session ID.

## Files

| File | Purpose |
|------|---------|
| `agent.py` | LangGraph graph + MiniMax model + 6 coding tools |
| `governed_agent.py` | OpenBox wrapper + helper for programmatic chat (`invoke_agent`) + CLI |
| `server.py` | FastAPI server exposing `/api/chat` and serving the web UI |
| `web/` | Static frontend (HTML/CSS/JS) for the chat experience |
| `test_connections.py` | Verify keys before running |
| `.env` | Your credentials (never commit this) |

## Upgrading to MiniMax M3

When M3 becomes free on OpenRouter, change one line in `agent.py`:

```python
# Before:
model="minimax/minimax-m2.5:free",

# After:
model="minimax/minimax-m3:free",
```

## View Governance Data

After running, go to: https://platform.openbox.ai
- **Agents** → MiniMax-Code-Agent → click your session
- See: event log, tool calls, LLM inputs/outputs, risk score, session replay
