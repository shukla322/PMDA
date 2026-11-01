import json
from pathlib import Path
from datetime import datetime,timezone
from pmda.reporting import report_learning

root=Path(__file__).resolve().parents[1]
source=root / "runtime/controlled-staged_learning-20261027T141258Z/fad7b8ac-4a90-4892-a454-87a0fe1911d7/outputs/rl_1.csv"
destination=root / "runtime" / ("rl-report-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
print(json.dumps(report_learning(source,destination),indent=2))
print(destination)
