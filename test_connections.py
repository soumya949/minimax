#!/usr/bin/env python3
# test_connections.py
# Run this FIRST to verify your keys before running governed_agent.py
# Usage: python test_connections.py

import os
import sys
import asyncio
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()

def check_env():
    """Check all required env vars are set."""
    print("\n[1/3] Checking environment variables...")
    required = [
        "OPENROUTER_API_KEY",
        "OPENBOX_URL",
        "OPENBOX_API_KEY",
        "OPENBOX_AGENT_DID",
        "OPENBOX_AGENT_PRIVATE_KEY",
    ]
    ok = True
    for var in required:
        val = os.getenv(var)
        if val:
            masked = val[:12] + "..." + val[-4:] if len(val) > 16 else "***"
            print(f"  ✓ {var} = {masked}")
        else:
            print(f"  ✗ {var} is NOT SET")
            ok = False
    return ok


def test_openrouter():
    """Ping OpenRouter with a minimal request."""
    print("\n[2/3] Testing OpenRouter → MiniMax M2.5 connection...")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "PASTE_YOUR_OPENROUTER_KEY_HERE":
        print("  ✗ OPENROUTER_API_KEY not set or still placeholder")
        return False

    data = json.dumps({
        "model": "minimax/minimax-m2.5",
        "messages": [{"role": "user", "content": "Reply with exactly: CONNECTED"}],
        "max_tokens": 20,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "connection-test",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            reply = resp["choices"][0]["message"]["content"]
            print(f"  ✓ MiniMax M2.5 responded: '{reply}'")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ✗ HTTP {e.code}: {body}")
        if "allowlist" in body.lower():
            print("  → Your OpenRouter key has a domain restriction.")
            print("  → Go to openrouter.ai/settings/keys and create a new key")
            print("     with NO domain restriction (leave the field blank).")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_openbox():
    """Verify OpenBox SDK can import and has credentials."""
    print("\n[3/3] Testing OpenBox SDK import...")
    try:
        from openbox_langgraph import create_openbox_graph_handler
        print("  ✓ openbox_langgraph imported successfully")

        url = os.getenv("OPENBOX_URL")
        key = os.getenv("OPENBOX_API_KEY")
        did = os.getenv("OPENBOX_AGENT_DID")
        pk  = os.getenv("OPENBOX_AGENT_PRIVATE_KEY")

        if all([url, key, did, pk]):
            print(f"  ✓ OPENBOX_URL        = {url}")
            print(f"  ✓ OPENBOX_API_KEY    = {key[:20]}...")
            print(f"  ✓ OPENBOX_AGENT_DID  = {did}")
            print(f"  ✓ PRIVATE_KEY set    = yes")
            return True
        else:
            print("  ✗ Some OpenBox env vars missing")
            return False
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        print("  → Run: pip install openbox-langgraph-sdk-python")
        return False


if __name__ == "__main__":
    print("=" * 55)
    print("  MiniMax + OpenBox Connection Test")
    print("=" * 55)

    env_ok       = check_env()
    openrouter_ok = test_openrouter()
    openbox_ok   = test_openbox()

    print("\n" + "=" * 55)
    print("RESULTS:")
    print(f"  Env vars    : {'✓ OK' if env_ok else '✗ FAIL'}")
    print(f"  OpenRouter  : {'✓ OK' if openrouter_ok else '✗ FAIL'}")
    print(f"  OpenBox SDK : {'✓ OK' if openbox_ok else '✗ FAIL'}")
    print("=" * 55)

    if env_ok and openrouter_ok and openbox_ok:
        print("\n✅ All checks passed! Run: python governed_agent.py")
    else:
        print("\n❌ Fix the issues above, then re-run this test.")
        sys.exit(1)
