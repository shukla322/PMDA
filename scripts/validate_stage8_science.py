"""Fixed held-out stratification and explicit reward-hacking challenge cases."""
import os
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
from pmda.registry import Registry
from pmda.predictor import FingerprintPredictor, metrics
from pmda.reward import ConservativeReward

ROOT = Path(__file__).resolve().parents[1]
run = ROOT / "runtime" / ("science-stage8-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
run.mkdir()
record = Registry(ROOT).optimization_predictor("EGFR-rf-v1")
directory = (ROOT / record.artifact.path).parent
predictor = FingerprintPredictor(directory)
test = json.loads((directory / "splits.json").read_bytes())["test"]
predictions = [predictor.predict(row["smiles"]) for row in test]
groups = {}
for name, indices in {"all":list(range(len(test))), "in_domain":[i for i,p in enumerate(predictions) if p["in_domain"]], "outside_domain":[i for i,p in enumerate(predictions) if not p["in_domain"]], "measured_pic50_le_5":[i for i,r in enumerate(test) if r["pic50"]<=5], "measured_pic50_ge_7":[i for i,r in enumerate(test) if r["pic50"]>=7]}.items():
    y = np.array([test[i]["pic50"] for i in indices]); yp = np.array([predictions[i]["value"] for i in indices])
    groups[name] = {"n":len(indices), "metrics":metrics(y,yp) if len(indices)>1 else None, "interval_coverage":float(np.mean([predictions[i]["lower"]<=test[i]["pic50"]<=predictions[i]["upper"] for i in indices])) if indices else None}
reward = ConservativeReward(directory, dict(model_sha256=record.artifact.sha256,required_smarts="c1ncnc2ccccc12"))
challenges = ["invalid", "", "CCO", "CC(=O)Oc1ccccc1C(=O)O", "[Na+].[Cl-]", "c1ccccc1", "C"*80, "CCOc1cc2ncnc(Nc3ccc(C)cc3)c2c2c1OCCO2"]
evaluated = reward.score(challenges)
assert all(row["reward"]==0 for row in evaluated["rows"][:-1])
assert evaluated["rows"][-1]["reward"]>0
report = {"predictor_sha256":record.artifact.sha256,"strata":groups,"reward_challenges":evaluated["rows"],"limitations":["Known training lead is a positive pipeline control, not independent validation", "Simple challenge structures are not property-matched decoys", "Only five weak-activity held-out examples; specificity is poorly characterized", "No external reviewer or prospective assay validation", "Generated distribution may invalidate empirical conformal coverage"]}
(run / "report.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
print(json.dumps({"strata":groups,"reward_challenges_passed":True,"report":str(run)},indent=2))
