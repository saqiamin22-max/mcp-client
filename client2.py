import streamlit as st
import asyncio
import os
import json

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import ToolMessage

load_dotenv()

MCP_KEY = os.getenv("MCP_API_KEY")

if not MCP_KEY:
    st.error("MCP_API_KEY missing")
    st.stop()

SERVERS = {
    "expense": {
        "transport": "streamable_http",
        "url": "https://leading-pink-lizard.fastmcp.app/mcp",
        "headers": {"Authorization": f"Bearer {MCP_KEY}"}
    },
    "expense-2": {
        "transport": "streamable_http",
        "url": "https://splendid-gold-dingo.fastmcp.app/mcp"
    },
    "manim-server": {
        "transport": "stdio",
        "command": "/Users/zubairali/Documents/odoo19/.venv/bin/python3",
        "args": [
            "/Users/zubairali/Desktop/manim-mcp-server/src/manim_server.py"
        ],
        "env": {
            "MANIM_EXECUTABLE": "/opt/anaconda3/bin/manim"
        }
    }
}

st.set_page_config(page_title="MCP AI Chat", layout="wide")
st.title("⚙️ MCP AI Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

# history show
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Type message...")

# -----------------------------
# MCP AGENT
# -----------------------------
async def run_agent_stream(prompt: str, placeholder):
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()
    tools_map = {t.name: t for t in tools}

    llm = ChatMistralAI()
    agent = llm.bind_tools(tools)

    # first response
    response = await agent.ainvoke(prompt)

    # tool call case
    if response.tool_calls:
        messages = []

        for call in response.tool_calls:
            name = call["name"]

            if name not in tools_map:
                continue

            args = call.get("args") or {}
            if isinstance(args, str):
                args = json.loads(args)

            result = await tools_map[name].ainvoke(args)

            messages.append(
                ToolMessage(
                    tool_call_id=call["id"],
                    content=str(result)
                )
            )

        final = await agent.ainvoke([prompt, response, *messages])
        text = final.content
    else:
        text = response.content

    # -------------------------
    # STREAM SIMULATION (typing effect)
    # -------------------------
    streamed = ""
    for char in text:
        streamed += char
        placeholder.markdown(streamed)
        await asyncio.sleep(0.01)

    return streamed


# -----------------------------
# CHAT FLOW
# -----------------------------
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()

        try:
            result = asyncio.run(run_agent_stream(user_input, placeholder))

            st.session_state.messages.append({
                "role": "assistant",
                "content": result
            })

        except Exception as e:
            placeholder.error(str(e))