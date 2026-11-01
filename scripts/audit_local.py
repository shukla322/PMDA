"""Check that active project code, packages, and scientific assets live in BTP.

System Python's standard library and operating-system DLLs are prerequisites.
This is a dependency-origin check, not an operating-system security sandbox.
"""
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

ROOT = Path(__file__).resolve().parents[1]


def require_local(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise RuntimeError(f"Project dependency outside BTP: {resolved}")
    return str(resolved.relative_to(ROOT))


def main():
    origins = {"interpreter": require_local(sys.executable)}
    for name in ("pmda", "pmda.agents", "pmda.reward", "requests", "reinvent", "reinvent_plugins", "torch", "rdkit", "mcp", "numpy", "pandas", "pydantic"):
        module = importlib.import_module(name)
        # Setuptools namespaces include a synthetic path-hook token, not a directory.
        paths = [module.__file__] if module.__file__ else [p for p in module.__path__ if not p.endswith(".__path_hook__")]
        if not paths or any(not Path(p).exists() for p in paths):
            raise RuntimeError(f"Missing physical module origin: {name}")
        origins[name] = [require_local(path) for path in paths]
    distributions = {}
    for dist in importlib.metadata.distributions():
        require_local(dist.locate_file(""))
        direct = dist.read_text("direct_url.json")
        if direct:
            url = urlparse(json.loads(direct)["url"])
            if url.scheme == "file":
                require_local(url2pathname(unquote(url.path)))
        distributions[dist.metadata["Name"]] = dist.version
    assets = {}
    for relative in ("models/reinvent_pubchem.prior", "models/mol2mol_medium_similarity.prior", "vendor/solitarius-mcp/server.py", "vendor/solitarius-mcp/config_builders/tl_config.py", "vendor/solitarius-mcp/config_builders/rl_config.py", "vendor/REINVENT4/LICENSE", "vendor/solitarius-mcp/LICENSE"):
        path = ROOT / relative
        require_local(path)
        assets[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if hashlib.md5((ROOT / "models/reinvent_pubchem.prior").read_bytes()).hexdigest() != "75052d5e93b2470e9c6684d369704f5f":
        raise RuntimeError("Unexpected sampling prior checksum")
    agent_provenance = ROOT / "models/agents/provenance.json"
    if agent_provenance.exists():
        for record in json.loads(agent_provenance.read_bytes())["assets"]:
            path = ROOT / record["path"]
            require_local(path)
            with path.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != record["sha256"]:
                raise RuntimeError("Agent asset checksum mismatch")
            assets[record["path"]] = actual
        servers = list((ROOT / "vendor/llama.cpp/bin").rglob("llama-server.exe"))
        if len(servers) != 1:
            raise RuntimeError("Missing or ambiguous BTP inference server")
        require_local(servers[0])
        assets[str(servers[0].relative_to(ROOT))] = hashlib.sha256(servers[0].read_bytes()).hexdigest()
    report = {"status": "passed", "scope": "Active import and distribution origins plus required assets", "origins": origins,
              "system_python": sys.base_prefix, "assets_sha256": assets, "packages": distributions}
    output = ROOT / "runtime" / "local-dependency-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "origins": origins, "distribution_count": len(distributions), "report": str(output)}, indent=2))


if __name__ == "__main__":
    main()
