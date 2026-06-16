#!/usr/bin/env python3
# test_policy_overwrite.py
# Targeted OpenBox policy test for: prompt contains "overwrite" -> BLOCK

import asyncio
import traceback
from governed_agent import run


async def main():
    prompt = (
        "Policy trigger test: overwrite. "
        "Do not use tools. Do not execute anything. Only say POLICY_TEST."
    )
    try:
        await run(prompt, session_id="policy-overwrite-002")
        print("\nRESULT: Agent run completed (NOT blocked). Check OpenBox policy evaluation.")
    except Exception:
        print("\nRESULT: Agent run stopped by governance. BLOCK/HALT likely enforced.")
        print("Check OpenBox trace/session: policy-overwrite-002")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
