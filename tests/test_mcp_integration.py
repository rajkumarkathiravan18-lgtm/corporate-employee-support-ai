import asyncio

from backend.mcp.client import invoke


def test_local_mcp_stdio_queries_real_server():
    async def check():
        balance = await invoke("leave_balance", "EMP001")
        assert '"casual": 5' in balance
        assert await invoke("claim_status", "EMP001", claim_id="CLM100") == "Under review"
        assert await invoke("claim_status", "EMP002", claim_id="CLM100") == "No claim found for your account"
    asyncio.run(check())
