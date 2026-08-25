"""
app.py

Streamlit chat UI for the Business Intelligence Agent.
Run: streamlit run app.py

Each question rebuilds the monday MCP client + agent inside a single
asyncio.run() call, rather than caching an agent across reruns. The MCP
client holds resources tied to whichever asyncio event loop created it,
and Streamlit reruns this whole script on every interaction — caching
the client risks reusing a connection whose loop has already been torn
down. Reconnecting each turn costs a bit of latency but avoids that
entire class of bug. Revisit this only if reconnect time becomes an
actual problem once things are stable.

Because the agent is already rebuilt fresh on every turn, detecting
"leadership update" style questions and passing that into build_agent
costs nothing extra structurally — it only changes which system prompt
variant gets used for that one turn (see agent.py's LEADERSHIP_BLOCK).
"""

import asyncio

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from agent import build_agent

# Keep in sync with MAX_HISTORY_MESSAGES in main.py — same reasoning:
# unbounded history eventually exceeds Groq's free-tier TPM limit even
# with a tight system prompt and minimal tools.
MAX_HISTORY_MESSAGES = 12

# Simple keyword check to detect leadership-update style requests, so the
# extra LEADERSHIP_BLOCK instructions (see agent.py) only get sent — and
# only cost tokens — on turns that actually need them, not on every
# routine question. Deliberately cheap/heuristic rather than an extra LLM
# call, to avoid spending more of the tight token budget just to decide
# whether to spend more of the tight token budget.
LEADERSHIP_KEYWORDS = (
    "leadership",
    "exec summary",
    "executive summary",
    "board update",
    "summarize for",
    "summarise for",
)


def is_leadership_request(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in LEADERSHIP_KEYWORDS)


st.set_page_config(page_title="Business Intelligence Agent", page_icon="📊")
st.title("📊 Business Intelligence Agent")
st.caption(
    "Ask about Work Orders and Deals. Strictly read-only — never modifies your boards."
)

if "messages" not in st.session_state:
    st.session_state.messages = []  # list of LangChain message objects

# Render prior turns on every rerun (Streamlit doesn't persist the DOM itself)
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage) and msg.content:
        # Skip AIMessages that only carry tool calls with no content —
        # those are intermediate ReAct steps, not something to show.
        with st.chat_message("assistant"):
            st.markdown(msg.content)


async def run_agent(conversation, leadership_mode: bool):
    agent = await build_agent(leadership_mode=leadership_mode)
    result = await agent.ainvoke({"messages": conversation})
    return result["messages"]


user_input = st.chat_input("Ask a business question...")

if user_input:
    st.session_state.messages.append(HumanMessage(content=user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    leadership_mode = is_leadership_request(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                updated_messages = asyncio.run(
                    run_agent(st.session_state.messages, leadership_mode)
                )
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.stop()

        reply = updated_messages[-1]
        st.markdown(reply.content)

    # Cap history the same way main.py does, to stay under the TPM budget
    st.session_state.messages = updated_messages[-MAX_HISTORY_MESSAGES:]
