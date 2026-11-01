import json
import math
from datetime import datetime,timezone
from pathlib import Path
from pmda.predictor import fit

root=Path(__file__).resolve().parents[1]
original=root / "models/egfr-20261027T135452Z"
output=root / "runtime" / ("science-reproduction-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
report=fit(root / "data/curated/egfr-20261027T135452Z/curated.json",output)
baseline=json.loads((original / "report.json").read_bytes())
for name in ("mae","rmse","r2","spearman"):
    if not math.isclose(report["test"][name],baseline["test"][name],rel_tol=1e-10,abs_tol=1e-10):
        raise RuntimeError("Scientific reproduction differs: "+name)
a=json.loads((original / "model.json").read_bytes())
b=json.loads((output / "model.json").read_bytes())
if a!=b:
    raise RuntimeError("Exported tree model differs")
result={"status":"passed","source":str(original.relative_to(root)),"replica":str(output.relative_to(root)),
        "model_json_exact_match":True,"heldout_metrics_match_tolerance":1e-10}
(output / "reproduction.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
