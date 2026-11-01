"""Build a readable report from recorded campaign evidence; never infer success."""
from collections import Counter
import json
from pathlib import Path
import sys
from pmda.store import Store

ROOT = Path(__file__).resolve().parents[1]


def main(directory):
    run = Path(directory).resolve()
    if not run.is_relative_to(ROOT / "runtime"):
        raise ValueError("Report input must be a BTP runtime campaign")
    summary = json.loads((run / "summary.json").read_bytes())
    cid = summary["campaign"]
    base = run / cid
    store = Store(run)
    store.verify_history(cid)
    lead = json.loads((base / "lead-selection.json").read_bytes())
    lines = ["# EGFR campaign results", "", "This report describes a bounded computational development demonstration, not drug discovery or experimental validation.", "",
             f"Controller state: **{summary['state']}**. Frozen scientific criteria met: **{summary['scientific_criteria_met']}**.", "",
             "## Fixed inputs", "", f"Lead SMILES: `{lead['lead']['smiles']}`", "",
             f"Training-record pIC50: {lead['lead']['pic50']:.4f}. This is a curated public assay aggregate; it is not a measurement of any generated analogue.", "",
             "Target: human wild-type EGFR. Predictor: EGFR-rf-v1. Dataset, model, recipe, seed and acceptance policy are recorded with hashes in the campaign inputs and approvals.", "",
             "## Observed iterations", "", "| Iteration | Mode | Rows | Portfolio size | Mean reward | Criteria met |", "|---|---|---:|---:|---:|---|"]
    for row in summary["iterations"]:
        lines.append(f"| {row['iteration']} | {row['run_type']} | {row['samples']} | {row['portfolio_size']} | {row['mean_reward']:.4f} | {row['criteria_met']} |")
    lines.extend(["", "RL trajectory and independent samples are different populations with small, unequal sample counts. This table does not establish an optimization improvement or causal treatment effect.", "", "## Rejection evidence", ""])
    for row in summary["iterations"]:
        directory = base / f"iteration-{row['iteration']}"
        evaluation = json.loads((directory / "evaluation/evaluation.json").read_bytes())
        reasons = Counter(reason for molecule in evaluation["rows"] for reason in molecule.get("rejection_reasons", []))
        lines.append(f"Iteration {row['iteration']}: {evaluation['summary']['valid']}/{evaluation['summary']['total']} valid structures. Rejection reasons may overlap: " + ", ".join(f"{key}={value}" for key, value in sorted(reasons.items())) + ".")
        lines.append("")
    selected = json.loads((base / "final-portfolio.json").read_bytes())
    lines.extend(["## Final independently sampled portfolio", "", "| SMILES | Predicted pIC50 | Lower bound | Upper bound | Evidence |", "|---|---:|---:|---:|---|"])
    for row in selected:
        activity = row["activity"]
        lines.append(f"| `{row['canonical_smiles']}` | {activity['value']:.3f} | {activity['lower']:.3f} | {activity['upper']:.3f} | Computational, level {row['evidence_level']} |")
    if not selected:
        lines.extend(["", "No independently sampled candidate met all portfolio rules. This is an explicit negative result; no substitute structures were inserted."])
    calls = list(base.glob("iteration-*/agents/*/attempt-*.json"))
    attempts = [json.loads(p.read_bytes()) for p in calls]
    lines.extend(["", "## Agent and approval evidence", "", f"Recorded {len(attempts)} real local inference attempts, including {sum(bool(a['accepted']) for a in attempts)} accepted role responses. Invalid responses remain in the record. Reviewed explanation choices and deterministic routing checks limit what these small-model agents can claim.", "", summary["authorization"], "",
        "## Limits and next scientific work", "", "- Predictions are not measured activity, selectivity, safety, efficacy or synthesis feasibility.",
        "- Conformal intervals are broad and calibration coverage under generated-molecule distribution shift is unproven.",
        "- Novelty is relative to the training partition only. Generator-training overlap, patents and global novelty were not assessed.",
        "- PAINS/Brenk exclusions are conservative review rules, not toxicity determinations.",
        "- A larger equal-budget multi-seed baseline comparison and independent medicinal-chemistry review are needed before interpreting effectiveness.",
        "- Review failures and the original thresholds before approving any larger campaign; do not silently relax criteria.", "",
        "## Reproduce or inspect", "", "From BTP: `.venv\\Scripts\\python.exe scripts\\run_egfr_campaign.py` starts a fresh bounded run. First install the local inference assets using `scripts/setup_agent_runtime.py`. See `docs/STAGES_6_7.md` for dependencies and scope.", "",
        "Use `TASK_PLAN.md`, `iteration-comparison.json`, `inputs.json`, the SQLite event ledger, role context/response archives, job logs and evaluation JSON/Parquet for detailed evidence. This report does not overwrite those records."])
    (base / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(base / "REPORT.md")


if __name__ == "__main__":
    main(sys.argv[1])
