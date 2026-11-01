"""Curate and fit the first research model; preserve failed qualification honestly."""
from datetime import datetime, timezone
import json
from pathlib import Path
from pmda.dataset import curate
from pmda.predictor import fit

root = Path(__file__).resolve().parents[1]
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
dataset = root / "data" / "curated" / ("egfr-" + stamp)
model = root / "models" / ("egfr-" + stamp)
report = curate(root / "data/raw/egfr-20261027T134420Z", dataset)
print(json.dumps(report, indent=2), flush=True)
print(json.dumps(fit(dataset / "curated.json", model), indent=2), flush=True)
print(f"Dataset: {dataset}\nModel: {model}", flush=True)
