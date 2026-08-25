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
"""

import asyncio

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from agent import build_agent

# Keep in sync with MAX_HISTORY_MESSAGES in main.py — same reasoning:
# unbounded history eventually exceeds Groq's free-tier TPM limit even
# with a tight system prompt and minimal tools.
MAX_HISTORY_MESSAGES = 12

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


async def run_agent(conversation):
    agent = await build_agent()
    result = await agent.ainvoke({"messages": conversation})
    return result["messages"]


user_input = st.chat_input("Ask a business question...")

if user_input:
    st.session_state.messages.append(HumanMessage(content=user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                updated_messages = asyncio.run(run_agent(st.session_state.messages))
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.stop()

        reply = updated_messages[-1]
        st.markdown(reply.content)

    # Cap history the same way main.py does, to stay under the TPM budget
    st.session_state.messages = updated_messages[-MAX_HISTORY_MESSAGES:]