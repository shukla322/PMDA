"""Four genuine local model calls; not a comprehensive agent benchmark."""
from datetime import datetime, timezone
import json
from pathlib import Path
from pmda.agents import LocalProvider, propose
from pmda.local_runtime import local_server

ROOT = Path(__file__).resolve().parents[1]
run = ROOT / "runtime" / ("live-agents-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
contexts = {
    "planner": dict(objective="Research-only EGFR analogue prioritization", target="EGFR-human-wt-v1", predictor="EGFR-rf-v1", missing_information=[]),
    "formulator": dict(predictor="EGFR-rf-v1", component="conservative_activity_v1", qualification=True),
    "executor": dict(run_type="sampling", approved=False, config_sha256="0" * 64),
    "analyser": dict(qualified=True, execution_succeeded=True, criteria_met=False, remaining_iterations=0, candidate_count=0),
}
results = {}
with local_server(run / "server") as url:
    provider = LocalProvider(url)
    for role, context in contexts.items():
        results[role] = propose(role, context, provider, run / role).model_dump()
        print(role, results[role], flush=True)
(run / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(run, flush=True)
