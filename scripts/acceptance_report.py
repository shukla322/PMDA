"""Verify delivered evidence without confusing local checks with production release."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from pmda.registry import Registry

root=Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((root / path).read_bytes())
def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()
tests=read("runtime/verification/tests.json")
if tests["status"]!="passed" or tests["skipped"]:
    raise RuntimeError("Regression suite is not fully passing")
for relative,expected in tests["source_sha256"].items():
    if sha(root / relative)!=expected:
        raise RuntimeError("Code changed after regression evidence: "+relative)
archive=read("environment/manifest.json")
if sha(root / "environment" / archive["archive"])!=archive["sha256"]:
    raise RuntimeError("Environment archive checksum mismatch")
if read("runtime/local-dependency-audit.json")["status"]!="passed":
    raise RuntimeError("Dependency origin audit did not pass")
if read("runtime/security-scan.json")["findings"]:
    raise RuntimeError("Secret scan requires review")
controlled={}
failure_paths={}
for path in sorted((root / "runtime").glob("controlled-*/summary.json")):
    data=json.loads(path.read_bytes())
    if data["status"]!="passed":
        continue
    if data.get("expected"):
        failure_paths[data["expected"]]=str(path.relative_to(root))
        continue
    identity=path.parent / data["campaign"] / "config-identity.json"
    if identity.exists() and json.loads(identity.read_bytes())["exact_bytes"]:
        campaign=path.parent / data["campaign"]
        expected=(campaign / "proposed.toml").read_bytes()
        executed=(campaign / "jobs" / data["job"] / "approved.toml").read_bytes()
        if expected!=executed:
            raise RuntimeError("Recorded exact-config identity no longer holds")
        controlled[data["kind"]]=str(path.relative_to(root))
if set(controlled)!={"sampling","mol2mol","transfer_learning","staged_learning"}:
    raise RuntimeError("Missing exact-config MCP integration evidence: "+str(controlled))
if set(failure_paths)!={"cancelled","timed_out"}:
    raise RuntimeError("Missing failure-path integration evidence")
registry=Registry(root)
predictor=registry.optimization_predictor("EGFR-rf-v1")
model_report=json.loads((root / predictor.report.path).read_bytes())
reproduction=read("runtime/science-reproduction-20261027T142920Z/reproduction.json")
if reproduction["status"]!="passed":
    raise RuntimeError("Scientific reproduction failed")
baseline=read("runtime/baseline-20261027T141908586203Z/result.json")
environment=read("runtime/baseline-20261027T141908586203Z/environment.json")
if baseline["status"]!="passed" or "recreated-py312" not in environment["executable"]:
    raise RuntimeError("Fresh environment baseline missing")
schemas=sorted(p.name for p in (root / "schemas/v1").glob("*.schema.json"))
report={"status":"local_mvp_checks_passed","timestamp":datetime.now(timezone.utc).isoformat(),
    "tests":tests["tests_run"],"schemas":schemas,"controlled_mcp_runs":controlled,"failure_path_runs":failure_paths,
    "fresh_environment_baseline":"runtime/baseline-20261027T141908586203Z",
    "scientific_model_report":predictor.report.path,"model_test_metrics":model_report["test"],
    "science_reproduction":reproduction,"cuda":"RTX 3060 Laptop GPU detected (Windows driver 31.0.15.4630); CUDA execution not verified because the pinned runtime is CPU-only",
    "scope":"Trusted single-user Windows CPU research MVP; not a production release or final research benchmark",
    "remaining_boundaries":["LLM specialists and target-specific end-to-end optimization are later stages",
        "Registered EGFR model is not yet a REINVENT RL reward; RL smoke uses QED",
        "Network authentication, container isolation and kernel resource quotas are deployment work",
        "Model has shared-publication and broad-interval limitations; see model card",
        "Historical external credential status is unverified; BTP uses no API key",
        "Host power-loss, cross-machine and GPU testing were not performed"]}
output=root / "runtime/verification/acceptance.json"
output.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"status":report["status"],"tests":report["tests"],"schema_count":len(schemas),"mcp_run_types":list(controlled),"report":str(output)},indent=2))
