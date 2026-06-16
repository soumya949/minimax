#!/usr/bin/env python3
# test_block_demo.py
# Quick verification that an OpenBox BLOCK policy fires on a neutral keyword.
#
# WHY a neutral keyword?
#   "nude" gets refused by the MiniMax model itself (built-in safety), so the
#   request never produces an OpenBox block you can show. A neutral trigger word
#   (the model has no objection to it) lets OpenBox be the ONLY thing that blocks
#   the session -- exactly what you want to demo.
#
# Usage:
#   python test_block_demo.py                  # uses default trigger
#   python test_block_demo.py "my-trigger"     # test your own keyword

import asyncio
import sys
import traceback

from governed_agent import invoke_agent

# This MUST match the VALUE in your OpenBox rule:
#   Field: messages.content   Operator: contains   Value: <DEFAULT_TRIGGER>   Decision: BLOCK
DEFAULT_TRIGGER = "blockmenow"


async def main():
    trigger = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TRIGGER
    prompt = f"This is a governance demo. Trigger keyword: {trigger}. Please just acknowledge."

    print("=" * 64)
    print(f"Sending prompt containing trigger -> '{trigger}'")
    print("=" * 64)

    try:
        final, _ = await invoke_agent([("user", prompt)], session_id="block-demo-001")
        print("\nRESULT: ALLOWED (not blocked).")
        print(f"Agent reply: {final}")
        print("\n-> If you expected a BLOCK, your OpenBox rule for this keyword")
        print("   is either not published or the VALUE does not match the keyword above.")
    except Exception:
        print("\nRESULT: BLOCKED by OpenBox governance. OK")
        print("Check the OpenBox dashboard session: block-demo-001")
        print("https://platform.openbox.ai")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
