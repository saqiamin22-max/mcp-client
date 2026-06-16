import asyncio
import os
import json

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import ToolMessage

load_dotenv()

# 🔐 API Key (required)
MCP_KEY = os.getenv("MCP_API_KEY")

if not MCP_KEY:
    raise ValueError("MCP_API_KEY missing in .env")

# 🔌 MCP Server
SERVERS = {
    "expense": {
        "transport": "streamable_http",
        "url": "https://leading-pink-lizard.fastmcp.app/mcp",
        "headers": {
            "Authorization": f"Bearer {MCP_KEY}"
        }
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


async def main():
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()

    tools_map = {t.name: t for t in tools}
    print("✅ Tools loaded:", list(tools_map.keys()))

    llm = ChatMistralAI()
    agent = llm.bind_tools(tools)

    prompt = ("Animate an equilateral triangle rotating uniformly about its"
              " center. Show angular velocity vector, circular motion"
              " of vertices, and plot the trajectory of one vertex."
              " Include equations of rotational motion on screen: θ = ωt.")
    response = await agent.ainvoke(prompt)

    # no tool use case
    if not response.tool_calls:
        print("\nLLM:", response.content)
        return

    messages = []

    for call in response.tool_calls:
        name = call["name"]

        if name not in tools_map:
            print("⚠ Unknown tool:", name)
            continue

        args = call.get("args") or {}

        # safe JSON handling
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

    print("\n✅ FINAL OUTPUT:\n", final.content)


if __name__ == "__main__":
    asyncio.run(main())
