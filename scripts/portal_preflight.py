"""Fast startup checks for the supported local Windows research release."""
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
failures=[]
for module in ["fastapi","uvicorn","pmda","rdkit","torch","requests"]:
    try:
        imported=importlib.import_module(module)
        if imported.__file__ and not Path(imported.__file__).resolve().is_relative_to(ROOT):
            failures.append(module+" imports outside BTP")
    except ImportError:
        failures.append(module+" is not installed in BTP")
for relative in ["models/mol2mol_medium_similarity.prior","models/agents/qwen2.5-1.5b-instruct-q4_k_m.gguf","models/agents/provenance.json","registries/predictors/EGFR-rf-v1.json","web/index.html","web/presentation.js"]:
    if not (ROOT / relative).is_file():
        failures.append("Missing "+relative)
if not list((ROOT / "vendor/llama.cpp/bin").rglob("llama-server.exe")):
    failures.append("Local model server is missing")
print("PMDA local startup check: "+("FAILED" if failures else "READY"))
for failure in failures:
    print("- "+failure)
raise SystemExit(bool(failures))
