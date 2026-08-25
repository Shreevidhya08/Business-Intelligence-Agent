"""
main.py

Simple command-line chat loop to test the agent before wiring up a UI.
Run: python main.py
"""

import asyncio

from langchain_core.messages import HumanMessage

from agent import build_agent

# Full history (including tool call results, which can be large raw GraphQL
# dumps) gets re-sent on every turn. Left unbounded, a session that started
# fine will eventually blow past Groq's free-tier TPM limit on its own even
# with a lighter system prompt and fewer tools. Keeping only the most recent
# messages trades long-range memory for staying under the limit — bump this
# up if you're on a paid Groq tier with more headroom.
MAX_HISTORY_MESSAGES = 12


async def main():
    print("Building agent (connecting to monday MCP)...")
    agent = await build_agent()
    print("Ready. Ask a business question (or type 'exit').\n")

    conversation = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        conversation.append(HumanMessage(content=user_input))

        result = await agent.ainvoke({"messages": conversation})
        reply = result["messages"][-1]
        print(f"\nAgent: {reply.content}\n")

        conversation = result["messages"][-MAX_HISTORY_MESSAGES:]  # cap history


if __name__ == "__main__":
    asyncio.run(main())