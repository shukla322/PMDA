"""Explicit stdio MCP access with structured failures and bounded waits."""

from contextlib import asynccontextmanager
from datetime import timedelta
import json
import os
from pathlib import Path


@asynccontextmanager
async def session(python, server, workdir, stderr):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.update(SERVER_TRANSPORT="stdio", REINVENT_CWD=str(Path(workdir).resolve()),
               MPLCONFIGDIR=str(Path(workdir).resolve() / ".matplotlib"),
               OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", PYTHONUTF8="1")
    env["PATH"] = str(Path(python).resolve().parent) + os.pathsep + env.get("PATH", "")
    params = StdioServerParameters(command=str(Path(python).resolve()),
                                  args=[str(Path(server).resolve())], env=env, cwd=str(Path(workdir).resolve()))
    with Path(stderr).open("w", encoding="utf-8") as err:
        async with stdio_client(params, errlog=err) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(minutes=5)) as client:
                await client.initialize()
                yield client


async def call(client, name, arguments):
    result = await client.call_tool(name, arguments)
    data = result.structuredContent
    if data is None:
        data = json.loads("\n".join(c.text for c in result.content if c.type == "text"))
    if result.isError or (isinstance(data, dict) and (data.get("error") or data.get("status") in {"failed", "error"})):
        raise RuntimeError(f"MCP tool {name} reported failure: {data}")
    return data
