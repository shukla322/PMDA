"""Run regression tests and retain a machine-readable acceptance record."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from datetime import datetime,timezone

root=Path(__file__).resolve().parents[1]
output=root / "runtime/verification"
output.mkdir(parents=True,exist_ok=True)
suite=unittest.defaultTestLoader.discover(str(root / "tests"))
with (output / "tests.log").open("w",encoding="utf-8") as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ("src/pmda","tests") for p in sorted((root / folder).rglob("*.py"))}
report={"status":"passed" if result.wasSuccessful() else "failed","tests_run":result.testsRun,
        "failures":[str(case) for case,_ in result.failures],"errors":[str(case) for case,_ in result.errors],
        "skipped":[str(case) for case,_ in result.skipped],"executable":sys.executable,
        "timestamp":datetime.now(timezone.utc).isoformat(),"source_sha256":sources}
(output / "tests.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k!="source_sha256"},indent=2))
raise SystemExit(not result.wasSuccessful())
