"""Bounded infrastructure smoke run authorized by the development task.

This is not a pharmaceutical campaign or a replacement for campaign approvals.
All project inputs and generated files stay in BTP.
"""
import asyncio
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tomllib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pmda.mcp_client import call, session
from pmda.evaluation import evaluate


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")


async def main():
    import torch
    from reinvent.validation import ReinventConfig
    server = ROOT / "vendor" / "solitarius-mcp" / "server.py"
    run = ROOT / "runtime" / ("baseline-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run.mkdir(parents=True)
    model = ROOT / "models" / "reinvent_pubchem.prior"
    if hashlib.md5(model.read_bytes()).hexdigest() != "75052d5e93b2470e9c6684d369704f5f":
        raise RuntimeError("Prior checksum differs from recorded upstream metadata")
    save(run / "environment.json", {"python": sys.version, "executable": sys.executable,
         "cuda": torch.cuda.is_available(), "packages": {p: importlib.metadata.version(p) for p in ("torch", "rdkit", "mcp", "pydantic")},
         "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest()})
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True)
    (run / "environment-observed.txt").write_text(freeze.stdout, encoding="utf-8")
    print(f"Baseline artifacts: {run}", flush=True)
    async with session(sys.executable, server, run, run / "mcp.stderr.log") as client:
        listing = await client.list_tools()
        save(run / "tools.json", [tool.model_dump(mode="json") for tool in listing.tools])
        args = {"model_file": str(model), "num_smiles": 100, "device": "cpu",
                "unique_molecules": False, "randomize_smiles": True,
                "output_file": str(run / "sampling.csv"), "workdir": str(run)}
        preview = await call(client, "reinvent_sampling", {**args, "dry_run": True})
        config = preview["config_toml"]
        ReinventConfig(**tomllib.loads(config))
        (run / "preview.toml").write_text(config, encoding="utf-8")
        result = await call(client, "reinvent_sampling", {**args, "dry_run": False})
        save(run / "sampling_response.json", result)
        actual = Path(result["config_path"]).read_text(encoding="utf-8")
        if tomllib.loads(actual) != tomllib.loads(config):
            raise RuntimeError("Executed configuration differs from preview")
    with (run / "sampling.csv").open(encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    column = next((k for k in records[0] if k.lower() == "smiles"), None)
    if column is None or len(records) != 100:
        raise RuntimeError("Unexpected sampling output schema/count")
    evidence = evaluate([r[column] for r in records])
    save(run / "evaluation.json", evidence)
    save(run / "result.json", {"status": "passed", "scope": "CPU MCP sampling and deterministic descriptors only", **evidence["summary"]})
    print(json.dumps(evidence["summary"], indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
