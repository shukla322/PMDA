"""MCP is a proposal/inspection boundary; it never owns campaign execution."""
import hashlib
import json
from pathlib import Path
import jsonschema
from .mcp_client import call
from .execution import validate_config

BUILDERS={"sampling":"reinvent_sampling","transfer_learning":"reinvent_transfer_learning","staged_learning":"reinvent_reinforcement_learning"}
READ_TOOLS={"reinvent_validate_toml","reinvent_job_status","reinvent_plot_rl_history","reinvent_analyze_molecules"}


async def discover(client):
    listing=await client.list_tools()
    tools={tool.name:tool.model_dump(mode="json") for tool in listing.tools}
    missing=set(BUILDERS.values())-set(tools)
    if missing:
        raise ValueError("Missing required MCP tools: "+", ".join(sorted(missing)))
    for name in BUILDERS.values():
        if "dry_run" not in tools[name]["inputSchema"].get("properties",{}):
            raise ValueError("MCP builder lacks required dry-run boundary")
    return {"tools":tools,"schema_sha256":hashlib.sha256(json.dumps(tools,sort_keys=True).encode()).hexdigest(),
        "execution_policy":"MCP dry-run proposals only; ExecutionService owns launches",
        "blocked_tools":[n for n in tools if "custom_scoring" in n or "test_scoring" in n]}


async def propose(client,kind,arguments,campaign,budget):
    capabilities=await discover(client)
    tool=BUILDERS[kind]
    args=dict(arguments,dry_run=True)
    properties=capabilities["tools"][tool]["inputSchema"].get("properties",{})
    if "launch" in properties:
        args["launch"]=False
    if "skip_validation" in properties:
        args["skip_validation"]=False
    args["device"]="cpu"
    jsonschema.validate(args,capabilities["tools"][tool]["inputSchema"])
    result=await call(client,tool,args)
    config=result.get("config_toml")
    if not isinstance(config,str):
        raise ValueError("MCP did not provide TOML proposal")
    content=config.encode("utf-8")
    validate_config(content,campaign,budget)
    path=Path(campaign) / "proposed.toml"
    path.write_bytes(content)
    return {"path":str(path),"sha256":hashlib.sha256(content).hexdigest(),"capability_sha256":capabilities["schema_sha256"]}
