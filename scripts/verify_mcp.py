"""Actual SDK client/server handshake through Docker stdio, not a tool mock."""

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command="docker", args=["compose", "run", "--rm", "-T", "--no-deps", "mcp"],
        # Docker Desktop discovers its Compose plugin through the Windows profile.
        env=dict(os.environ),
    )
    async with stdio_client(params) as streams, ClientSession(*streams) as session:
        await session.initialize()
        tools = await session.list_tools()
        assert len(tools.tools) == 6
        search = await session.call_tool("search_vulnerabilities", {"page_size": 1})
        assert not search.isError
        data = json.loads(search.content[0].text)
        identifier = data["items"][0]["cve_id"]
        checks = {"initialize": "PASS", "list_six_readonly_tools": "PASS", "search_vulnerabilities": "PASS"}
        for name, args in (
            ("get_cve_details", {"cve_id": identifier}),
            ("get_top_cwes", {}),
            ("get_vulnerability_statistics", {}),
            ("get_affected_products", {}),
            ("explore_cve_relationships", {"cve_id": identifier}),
        ):
            result = await session.call_tool(name, args)
            assert not result.isError, name
            checks[name] = "PASS"
        invalid = await session.call_tool("get_cve_details", {"cve_id": "../../secrets"})
        assert invalid.isError
        checks["invalid_identifier_rejected"] = "PASS"
        result = {"at": datetime.now(UTC).isoformat(), "transport": "stdio", "cve": identifier, "checks": checks}
        Path("docs/evidence/mcp_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
