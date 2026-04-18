"""
FoodBridge Agent — Claude + MCP agentic loop.

Connects to the MCP server (mcp/server.py) via stdio, pulls tool definitions,
and runs an agentic loop: user message → Claude → tool calls → Claude → response.
"""

import asyncio
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5-20251001"
MCP_SERVER_PATH = Path(__file__).parent.parent / "mcp" / "server.py"

SYSTEM_PROMPT = """You are FoodBridge, a personalized nutrition and grocery assistant.

You help users:
- Build a health profile and calculate their daily nutritional needs
- Find foods from the USDA FoodData Central database
- Score and rank foods by nutrient density for their specific goals
- Plan weekly meals that meet their nutritional targets
- Generate a grocery list with estimated prices within their budget

Always be warm, practical, and health-focused. When a user first talks to you,
gather their profile information naturally through conversation before calling tools.
Guide them through the full flow: profile → preferences → food search → meal plan → grocery list.
"""


def _mcp_tool_to_anthropic(tool) -> dict:
    """Convert an MCP tool definition to Anthropic tool format."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.inputSchema,
    }


async def run_agent(
    user_message: str,
    conversation_history: list[dict],
) -> tuple[str, list[dict]]:
    """
    Run one turn of the agentic loop.

    Args:
        user_message: The user's latest message
        conversation_history: Full conversation so far (mutated in place)

    Returns:
        (assistant_response_text, updated_conversation_history)
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    server_params = StdioServerParameters(
        command="python3",
        args=[str(MCP_SERVER_PATH)],
        env={**os.environ},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Pull tool definitions from MCP server
            tools_result = await session.list_tools()
            tools = [_mcp_tool_to_anthropic(t) for t in tools_result.tools]

            # Append user message to history
            conversation_history.append({"role": "user", "content": user_message})

            # Agentic loop
            while True:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                    messages=conversation_history,
                )

                # Collect assistant message (may contain text + tool_use blocks)
                assistant_content = response.content
                conversation_history.append({
                    "role": "assistant",
                    "content": assistant_content,
                })

                # If Claude is done (no more tool calls), return final text
                if response.stop_reason == "end_turn":
                    final_text = " ".join(
                        block.text for block in assistant_content
                        if hasattr(block, "text")
                    )
                    return final_text, conversation_history

                # Execute all tool calls Claude requested
                tool_results = []
                for block in assistant_content:
                    if block.type != "tool_use":
                        continue

                    try:
                        result = await session.call_tool(block.name, arguments=block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result.content),
                        })
                    except Exception as exc:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {exc}",
                            "is_error": True,
                        })

                # Feed tool results back to Claude
                conversation_history.append({
                    "role": "user",
                    "content": tool_results,
                })


def run_agent_sync(
    user_message: str,
    conversation_history: list[dict],
) -> tuple[str, list[dict]]:
    """Synchronous wrapper for use in FastAPI endpoints."""
    return asyncio.run(run_agent(user_message, conversation_history))