"""Test-only protocol server: no chemistry execution and no filesystem mutations."""
from mcp.server.fastmcp import FastMCP
server=FastMCP("pmda-fixture")

@server.tool()
def fixture_success(value: int) -> dict:
    return {"status":"ok","value":value}

@server.tool()
def fixture_failure() -> dict:
    return {"status":"failed","error":"intentional fixture failure"}

if __name__=="__main__":
    server.run(transport="stdio")
