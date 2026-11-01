"""Preregistered small-budget comparative experiment; records negative results."""
import os
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import traceback
from run_egfr_campaign import main, save

ROOT = Path(__file__).resolve().parents[1]
run = ROOT / "runtime" / ("benchmark-stage8-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
run.mkdir()
protocol = {"seeds": [42, 99], "arms": ["prior", "mol2mol", "no_feedback", "fixed", "full"],
    "candidate_budget": 48, "allocation_adaptive": [16, 16, 16], "engine_seconds_per_job": 600,
    "primary_metric": "final independent portfolio size under frozen Stage7 criteria",
    "limitations": ["Two seeds are a pilot, not a powered comparison", "Equal candidate ceilings, not equal training FLOPs or wall time; timings reported", "Current agents cannot change the scientific policy; fixed and full paths may be identical", "No external medicinal-chemist review"]}
save(run / "protocol.json", protocol)
results = []
for seed in protocol["seeds"]:
    for arm in protocol["arms"]:
        started = time.monotonic()
        record = {"seed": seed, "arm": arm}
        try:
            folder = main(seed, arm, (16, 16, 16), run / f"{arm}-{seed}")
            summary = json.loads((folder / "summary.json").read_bytes())
            record.update(status="executed", criteria_met=summary["scientific_criteria_met"],
                portfolio_size=summary["iterations"][-1]["portfolio_size"],
                generated_rows=sum(i["samples"] for i in summary["iterations"]), campaign=summary["campaign"],
                final_mean_reward=summary["iterations"][-1]["mean_reward"])
        except Exception as exc:
            record.update(status="error", error=str(exc))
            (run / f"{arm}-{seed}-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        record["wall_seconds"] = time.monotonic() - started
        results.append(record)
        save(run / "results.json", results)
        print("BENCHMARK", record, flush=True)
save(run / "decision.json", {"release": "local research alpha only", "adaptive_superiority_established": False,
    "all_runs_executed": all(r["status"] == "executed" for r in results), "limitations": protocol["limitations"]})
print("BENCHMARK_COMPLETE", run, flush=True)
