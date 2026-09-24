"""MCP tools backed by persistent fictional demonstration records."""

from mcp.server.fastmcp import FastMCP

from backend.mcp import storage

server = FastMCP("demo-corporate-records")


@server.tool()
def get_leave_balance(employee_id: str) -> dict:
    return storage.leave_balance(employee_id)


@server.tool()
def get_claim_status(employee_id: str, claim_id: str) -> str:
    return storage.claim_status(employee_id, claim_id)


@server.tool()
def get_ticket_status(employee_id: str, ticket_id: str) -> str:
    return storage.ticket_status(employee_id, ticket_id)


@server.tool()
def create_it_ticket(employee_id: str, issue: str) -> str:
    return storage.create_ticket(employee_id, issue)


if __name__ == "__main__":
    server.run(transport="stdio")
