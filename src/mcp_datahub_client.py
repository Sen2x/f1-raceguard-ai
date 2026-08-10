"""Agentic DataHub access through the official DataHub MCP Server.

Instead of calling the DataHub GraphQL API directly, this module drives the
``mcp-server-datahub`` process (https://github.com/acryldata/mcp-server-datahub)
as a Model Context Protocol tool server: it spawns the server over stdio,
lists its published tools, and invokes ``search`` / ``get_lineage`` on it the
same way an AI agent client (e.g. Claude Desktop) would.

The server is configured through the same environment variables DataHub's own
tooling uses:

- ``DATAHUB_GMS_URL``   (default: ``http://localhost:8080``)
- ``DATAHUB_GMS_TOKEN`` (optional personal access token)
"""

import asyncio
import os
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEFAULT_GMS_URL = "http://localhost:8080"
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("DATAHUB_MCP_TIMEOUT_SECONDS", "8"))

MCP_SERVER_COMMAND = os.environ.get("DATAHUB_MCP_COMMAND", sys.executable)
MCP_SERVER_ARGS = os.environ.get(
    "DATAHUB_MCP_ARGS",
    "-m mcp_server_datahub",
).split()


def _server_params() -> StdioServerParameters:
    env = {
        "DATAHUB_GMS_URL": os.environ.get("DATAHUB_GMS_URL", DEFAULT_GMS_URL),
        "DATAHUB_TELEMETRY_ENABLED": os.environ.get(
            "DATAHUB_TELEMETRY_ENABLED", "false"
        ),
    }

    token = os.environ.get("DATAHUB_GMS_TOKEN")
    if token:
        env["DATAHUB_GMS_TOKEN"] = token

    return StdioServerParameters(
        command=MCP_SERVER_COMMAND,
        args=MCP_SERVER_ARGS,
        env=env,
    )


async def _call_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    async def _run() -> Any:
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(tool_name, arguments)

                if result.isError:
                    raise RuntimeError(
                        f"DataHub MCP tool '{tool_name}' returned an error: {result.content}"
                    )

                return result.structuredContent

    return await asyncio.wait_for(_run(), timeout=DEFAULT_TIMEOUT_SECONDS)


async def list_available_tools() -> list[str]:
    """Lists the tools the DataHub MCP Server currently publishes."""

    async def _run() -> list[str]:
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [tool.name for tool in tools.tools]

    return await asyncio.wait_for(_run(), timeout=DEFAULT_TIMEOUT_SECONDS)


async def find_entity_urn(entity_name: str) -> str | None:
    """Uses the MCP `search` tool to resolve an entity name to its DataHub URN."""
    result = await _call_tool(
        "search",
        {"query": entity_name, "num_results": 1},
    )

    search_results = (result or {}).get("searchResults", [])
    if not search_results:
        return None

    return search_results[0]["entity"]["urn"]


async def get_downstream_entities(urn: str, max_results: int = 30) -> list[str]:
    """Uses the MCP `get_lineage` tool to fetch downstream impact for a URN."""
    result = await _call_tool(
        "get_lineage",
        {
            "urn": urn,
            "upstream": False,
            "max_results": max_results,
        },
    )

    downstreams = (result or {}).get("downstreams", {})
    search_results = downstreams.get("searchResults", [])

    return [item["entity"]["urn"] for item in search_results]


def get_downstream_entities_sync(urn: str, max_results: int = 30) -> list[str]:
    """Synchronous wrapper around `get_downstream_entities` for non-async callers."""
    return asyncio.run(get_downstream_entities(urn, max_results=max_results))


if __name__ == "__main__":
    async def _demo() -> None:
        tools = await list_available_tools()
        print("DataHub MCP tools available:", ", ".join(tools))

        urn = await find_entity_urn("primary_tyre_sensor")
        print(f"Resolved URN via MCP search: {urn}")

        if urn:
            downstream = await get_downstream_entities(urn)
            print("Downstream entities via MCP get_lineage:")
            for entity_urn in downstream:
                print(f"- {entity_urn}")

    asyncio.run(_demo())
