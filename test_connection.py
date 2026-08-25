"""
test_connection.py

Standalone script to verify the connection to monday.com's hosted MCP server
before wiring it into an LLM agent. Run this first — if it fails, fix the
connection here rather than debugging through the agent layer.

Usage:
    1. Make sure your .env file has MONDAY_TOKEN=your_token_here
    2. Activate your venv
    3. Run: python test_connection.py
"""

import asyncio
import os
import sys

# Windows' default console encoding (cp1252) can't handle some characters
# that appear in monday.com's tool descriptions (e.g. arrows like "->" as U+2192).
# Force UTF-8 so printing/redirecting to a file doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

MONDAY_TOKEN = os.environ.get("MONDAY_TOKEN")

if not MONDAY_TOKEN:
    raise RuntimeError(
        "MONDAY_TOKEN not found. Check that your .env file exists in this "
        "folder and contains a line like: MONDAY_TOKEN=your_token_here"
    )

# Optional: set this if you want to test pulling real items from a board.
# Find the board ID in the URL when you open a board in monday.com,
# e.g. https://yourteam.monday.com/boards/1234567890 -> 1234567890
# monday's MCP tools expect this as a number, not a string, so we convert it.
_raw_board_id = os.environ.get("WORK_ORDERS_BOARD_ID")
WORK_ORDERS_BOARD_ID = int(_raw_board_id) if _raw_board_id else None

client = MultiServerMCPClient(
    {
        "monday": {
            "transport": "streamable_http",
            "url": "https://mcp.monday.com/mcp",
            "headers": {"Authorization": f"Bearer {MONDAY_TOKEN}"},
        }
    }
)


async def main():
    print("Connecting to monday.com MCP server...")
    tools = await client.get_tools()

    if not tools:
        print("Connected, but no tools were returned. Check your token's permissions.")
        return

    print(f"\nConnected successfully. Found {len(tools)} tool(s):\n")
    for t in tools:
        print(f"  - {t.name}: {t.description}")

    if not WORK_ORDERS_BOARD_ID:
        print(
            "\n(Set WORK_ORDERS_BOARD_ID in your .env to also test a real data pull.)"
        )
        return

    tools_by_name = {t.name: t for t in tools}

    # Step 1: get_board_info FIRST — this is a documented required precondition
    # before get_board_items_page. It gives you real column IDs/types/labels,
    # which you need to make sense of (or later filter/query) the item data.
    board_info_tool = tools_by_name.get("get_board_info")
    if board_info_tool:
        print(f"\nCalling get_board_info for board {WORK_ORDERS_BOARD_ID} ...")
        try:
            info = await board_info_tool.ainvoke(
                {
                    "boardId": WORK_ORDERS_BOARD_ID,
                    "filters": {"columns": {"only": True}},
                }
            )
            print("\n--- get_board_info result ---\n")
            print(info)
        except Exception as e:
            print(f"\nget_board_info call failed: {e}")
            print(f"Check the exact expected args: {board_info_tool.args}")
    else:
        print("\nget_board_info tool not found in tool list — check spelling/availability.")

    # Step 2: Use execute_code to run a direct GraphQL query instead of
    # guessing get_board_items_page's exact parameter names. execute_code
    # runs in monday's authenticated sandbox — no token handling needed here,
    # and GraphQL syntax is fully documented, unlike the wrapped tool's schema.
    exec_tool = tools_by_name.get("execute_code")
    if exec_tool:
        print(f"\nCalling execute_code to fetch items + column values for board {WORK_ORDERS_BOARD_ID} ...")
        graphql_code = """
import requests

query = '''
{
  boards(ids: [%s]) {
    items_page(limit: 25) {
      cursor
      items {
        id
        name
        column_values {
          id
          text
          value
        }
      }
    }
  }
}
'''

resp = requests.post('https://api.monday.com/v2', json={'query': query})
body = resp.json()
if 'errors' in body:
    raise RuntimeError(body['errors'])
print(body['data'])
""" % WORK_ORDERS_BOARD_ID

        try:
            result = await exec_tool.ainvoke({"code": graphql_code})
            print("\n--- execute_code result (items + column values) ---\n")
            print(result)
        except Exception as e:
            print(f"\nexecute_code call failed: {e}")
            print(f"Check the exact expected args: {exec_tool.args}")
    else:
        print("\nexecute_code tool not found in tool list — check spelling/availability.")


if __name__ == "__main__":
    asyncio.run(main())