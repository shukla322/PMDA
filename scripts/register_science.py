"""Register immutable local dataset/model versions and export a candidate example."""
import hashlib
import json
from pathlib import Path
from pmda.registry import Registry
from pmda.evaluation import evaluate_registered,export_evaluation

root = Path(__file__).resolve().parents[1]
registry = Registry(root)
dataset = root / "data/curated/egfr-20261027T135452Z"
model = root / "models/egfr-20261027T135452Z"
curation = json.loads((dataset / "curation_report.json").read_bytes())
report = json.loads((model / "report.json").read_bytes())
def artifact(path):
    return {"path":str(path.relative_to(root)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"size":path.stat().st_size}
records = {
"targets":{"identifier":"EGFR-human-wt-v1","species":"Homo sapiens","construct_description":"Assay-described wild-type EGFR; CHEMBL203 / P00533",
           "mechanism":"Inhibition; covalent/noncovalent mechanism not inferred","endpoint":"pIC50","limitations":curation["limitations"]},
"datasets":{"identifier":"EGFR-curated-v1","target":"EGFR-human-wt-v1","artifact":artifact(dataset / "curated.json"),
           "source_manifest_sha256":curation["source_manifest_sha256"],"curation_version":curation["policy"],"endpoint":"pIC50",
           "split_policy":report["split"],"license_note":"Derived ChEMBL data: retain attribution and applicable source license; see TARGET_SELECTION.md"},
"predictors":{"identifier":"EGFR-rf-v1","target":"EGFR-human-wt-v1","dataset_sha256":report["dataset_sha256"],
           "artifact":artifact(model / "model.json"),"report":artifact(model / "report.json"),"endpoint":"pIC50",
           "intended_use":"Research-only ranking of in-domain compounds; not efficacy or clinical use",
           "domain_method":"Training Morgan Tanimoto threshold fixed from train leave-one-out neighbors",
           "uncertainty_method":"90% split-conformal absolute residual interval on held-out calibration scaffolds",
           "eligible_for_optimization":report["eligible_for_optimization"],"limitations":report["limitations"]}}
for kind,record in records.items():
    try:
        registry.register(kind,record)
    except FileExistsError:
        if registry.load(kind,record["identifier"]) != registry.TYPES[kind].model_validate(record):
            raise RuntimeError("Existing registry version differs; create a new identifier")
rows = json.loads((model / "splits.json").read_bytes())["test"]
result = evaluate_registered([r["smiles"] for r in rows[:20]],registry,"EGFR-rf-v1")
print(json.dumps(export_evaluation(result,root / "runtime/registered-egfr-evaluation"),indent=2))
