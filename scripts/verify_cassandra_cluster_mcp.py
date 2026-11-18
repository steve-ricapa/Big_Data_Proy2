"""Call the actual MCP SDK tools from the deployed MCP image against the live API."""

import asyncio
import json
import os
from datetime import UTC, datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    expected = {
        "search_vulnerabilities": {"page_size": 1},
        "get_cve_details": {"cve_id": "CVE-2024-0001"},
        "get_top_cwes": {},
        "get_vulnerability_statistics": {},
        "get_affected_products": {},
        "explore_cve_relationships": {"cve_id": "CVE-2024-0001"},
    }
    params = StdioServerParameters(command="python", args=["-m", "services.mcp_server.server"], env=dict(os.environ))
    async with stdio_client(params) as streams, ClientSession(*streams) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        assert {t.name for t in tools} == set(expected)
        checks = {}
        for tool in tools:
            result = await session.call_tool(tool.name, expected[tool.name])
            assert not result.isError and result.content, tool.name
            checks[tool.name] = {"status": "PASS", "input_fields": sorted(tool.inputSchema.get("properties", {}))}
        print(json.dumps({"at": datetime.now(UTC).isoformat(), "transport": "MCP stdio", "backend": os.environ["API_URL"], "public_oauth_e2e": False, "checks": checks}))


if __name__ == "__main__":
    asyncio.run(main())
