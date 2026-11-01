"""Derived plots and independent molecule analysis; raw job artifacts stay untouched."""
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
from .evaluation import evaluate,export_evaluation


def report_learning(csv_path,destination):
    root=Path(__file__).resolve().parents[2]
    source,destination=Path(csv_path).resolve(),Path(destination).resolve()
    if not source.is_relative_to(root) or not destination.is_relative_to(root):
        raise ValueError("Reports must use BTP-local inputs and outputs")
    destination.mkdir(parents=True,exist_ok=False)
    with source.open(encoding="utf-8") as stream:
        reader=csv.DictReader(stream)
        if not {"step","Score","SMILES"} <= set(reader.fieldnames or []):
            raise ValueError("Missing learning-history columns")
        rows=list(reader)
    groups=defaultdict(list)
    for row in rows:
        step=int(row["step"])
        score=float(row["Score"])
        if not math.isfinite(score):
            raise ValueError("Non-finite learning score")
        groups[step].append(score)
    if not groups:
        raise ValueError("Empty learning history")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    steps=sorted(groups)
    means=[statistics.mean(groups[step]) for step in steps]
    fig,ax=plt.subplots(figsize=(7,4),layout="constrained")
    ax.plot(steps,means,marker="o",color="#215c83")
    ax.set(xlabel="Learning step",ylabel="Mean configured reward",title="Bounded infrastructure learning history")
    ax.set_xticks(steps)
    ax.grid(alpha=.2)
    fig.savefig(destination / "learning.png",dpi=180)
    plt.close(fig)
    export_evaluation(evaluate([r["SMILES"] for r in rows]),destination / "molecules")
    report={"source":str(source.relative_to(root)),"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "rows":len(rows),"steps":steps,"mean_reward":means,
        "limitations":["Short infrastructure run, not evidence of converged learning or improved target potency"]}
    (destination / "report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
