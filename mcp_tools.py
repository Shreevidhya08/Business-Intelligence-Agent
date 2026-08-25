"""
mcp_tools.py

Connects to monday's hosted MCP server and returns a read-only-only
subset of its tools. Even though the assignment token should already be
scoped read-only at the monday.com permission level, this is a second,
code-level guardrail: we simply never hand the LLM any write/create/delete
tool, so it can't call one even if it wanted to.
"""

from langchain_mcp_adapters.client import MultiServerMCPClient

from config import MONDAY_MCP_URL, MONDAY_TOKEN

# Tools we actually want the agent to have access to. Everything else
# (create_item, create_items, create_update, vibe_*, action management,
# etc.) is left out on purpose — read-only enforcement at the code level,
# not just relying on the token's permissions.
#
# NOTE: get_board_items_page is deliberately excluded. Its schema has
# multiple boolean parameters (includeColumns, includeGroup, etc.), and
# every open model tested (gpt-oss-120b, qwen3.6-27b) generates Python-style
# True/False text instead of proper JSON booleans for them — Groq's backend
# validates strictly and rejects the call before it reaches our code. This
# is a known rough edge with boolean-heavy tool schemas on open models, not
# something fixable by swapping models again. execute_code (simple string
# params: code/language/description) works reliably and is used instead —
# see the system prompt for how the agent is told to fetch item data.
ALLOWED_TOOL_NAMES = {
    "get_board_info",
    "execute_code",  # only ever used here to run read (query) GraphQL, never mutations
}

# Previously also included get_updates, get_board_activity, and
# list_users_and_teams — dropped because they aren't used anywhere in the
# current workflow and each tool's schema (sent to the model on every call)
# adds fixed token overhead that was pushing requests over Groq's free-tier
# TPM limit. Add one back only if you actually need it, and re-check your
# token budget after.


def get_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            "monday": {
                "transport": "streamable_http",
                "url": MONDAY_MCP_URL,
                "headers": {"Authorization": f"Bearer {MONDAY_TOKEN}"},
            }
        }
    )


async def get_readonly_tools(client: MultiServerMCPClient):
    """Fetch monday's MCP tools and filter down to the read-only allowlist."""
    all_tools = await client.get_tools()
    filtered = [t for t in all_tools if t.name in ALLOWED_TOOL_NAMES]

    missing = ALLOWED_TOOL_NAMES - {t.name for t in filtered}
    if missing:
        print(f"Warning: expected tools not found on server: {missing}")

    return filtered