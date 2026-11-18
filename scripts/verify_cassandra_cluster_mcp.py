"""Call the actual MCP SDK tools from the deployed MCP image against the live API."""

import asyncio
import json
import os
from datetime import UTC, datetime

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    cve = "CVE-2024-0001"
    root = "/api/v1"
    expected = {
        "search_vulnerabilities": ({"page_size": 1, "cve_id": cve}, "/vulnerabilities", {"page": 1, "page_size": 1, "cve_id": cve}),
        "get_cve_details": ({"cve_id": cve}, f"/vulnerabilities/{cve}", {"view": "legacy", "include_applicability": False}),
        "get_top_cwes": ({}, "/cwes/top", {}),
        "get_vulnerability_statistics": ({}, "/kpis", {}),
        "get_affected_products": ({}, "/products/top", {"page": 1, "view": "legacy", "mode": "ranking"}),
        "explore_cve_relationships": ({"cve_id": cve}, f"/graph/cve/{cve}", {"page": 1, "page_size": 250}),
    }
    params = StdioServerParameters(command="python", args=["-m", "services.mcp_server.server"], env=dict(os.environ))
    async with stdio_client(params) as streams, ClientSession(*streams) as session, httpx.AsyncClient(base_url=os.environ["API_URL"], timeout=60) as api:
        await session.initialize()
        tools = (await session.list_tools()).tools
        assert {t.name for t in tools} == set(expected)
        checks = {}
        for tool in tools:
            args, path, query = expected[tool.name]
            result = await session.call_tool(tool.name, args)
            response = await api.get(root + path, params={**query, "include_metadata": True})
            response.raise_for_status()
            assert not result.isError and result.structuredContent and tool.outputSchema, tool.name
            assert result.structuredContent == json.loads(result.content[0].text) == response.json(), tool.name
            invalid = await session.call_tool(tool.name, {**args, "unexpected_audit_argument": True})
            assert invalid.isError, tool.name
            checks[tool.name] = {"status": "PASS", "structured_api_parity": True, "unknown_argument_rejected": True, "input_fields": sorted(tool.inputSchema.get("properties", {}))}
        print(json.dumps({"at": datetime.now(UTC).isoformat(), "transport": "MCP stdio", "backend": os.environ["API_URL"], "public_oauth_e2e": False, "checks": checks}))


if __name__ == "__main__":
    asyncio.run(main())
