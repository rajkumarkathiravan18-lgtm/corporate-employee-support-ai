"""Invoke the allowlisted demo MCP tools over stdio."""

import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALLOWED = {
    "leave_balance": "get_leave_balance",
    "claim_status": "get_claim_status",
    "ticket_status": "get_ticket_status",
    "create_it_ticket": "create_it_ticket",
}


async def invoke(action: str, employee_id: str, **params) -> str:
    if action not in ALLOWED:
        raise ValueError("Unsupported action")
    # The stdio subprocess starts at project root so backend imports work on Windows.
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.mcp.server"],
        cwd=str(PROJECT_ROOT),
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                ALLOWED[action], {"employee_id": employee_id, **params}
            )
            if result.isError:
                raise RuntimeError("The demo records service rejected the operation")
            if result.structuredContent:
                payload = result.structuredContent
                if isinstance(payload, dict) and set(payload) == {"result"}:
                    payload = payload["result"]
                return payload if isinstance(payload, str) else json.dumps(payload)
            return "\n".join(getattr(block, "text", "") for block in result.content)
