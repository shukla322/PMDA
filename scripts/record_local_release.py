"""Link observed evidence and current source hashes without inventing release gates."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(relative):
    return json.loads((ROOT / relative).read_bytes())

tests = read("runtime/verification/tests.json")
assert tests["status"] == "passed" and not tests["failures"] and not tests["errors"] and not tests["skipped"]
for relative, expected in tests["source_sha256"].items():
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, "Source changed after regression: " + relative
journey = read("runtime/portal-journey-20261029T042822Z/result.json")
restore = read("runtime/backups/20261029T043400Z/restore-drill.json")
assert journey["status"] == restore["status"] == "passed"
benchmark = read("runtime/benchmark-stage8-20261028T052759Z/decision.json")
diagnostics = read("runtime/agent-diagnostics-20261029T042616Z/results.json")
folder = ROOT / "runtime/releases" / ("local-v0.2.0-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
folder.mkdir(parents=True)
record = {"version":"0.2.0-local", "release_decision":"Local research demonstration; no public production promotion",
    "regression_tests":tests["tests_run"], "http_journey":journey, "restore_drill":restore,
    "benchmark":benchmark, "agent_cases":len(diagnostics["cases"]),
    "first_attempt_agent_passes":sum(c["first_attempt_passed"] for c in diagnostics["cases"]),
    "browser_visual_signoff":False, "browser_limitation":"Computer-use inventory returned no apps or browsers; native pipe unavailable",
    "source_sha256":{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for directory in ["src/pmda","scripts","web"] for path in sorted((ROOT / directory).rglob("*")) if path.is_file() and path.suffix in {".py",".js",".css",".html"} and "__pycache__" not in path.parts}}
(folder / "manifest.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
print(folder / "manifest.json")
