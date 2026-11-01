"""Short focused regression selection; does not claim a full-suite pass."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
names = ["test_agents_reward", "test_foundation.CampaignTests.test_cannot_skip_approval",
         "test_foundation.CampaignTests.test_changed_config_blocks_launch",
         "test_foundation.CampaignTests.test_concurrent_launch_only_once",
         "test_foundation.CampaignTests.test_changed_plan_blocks_launch",
         "test_foundation.CampaignTests.test_restart_preserves_state_and_ledger"]
run = ROOT / "runtime" / ("stage67-checks-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
run.mkdir(parents=True)
suite = unittest.defaultTestLoader.loadTestsFromNames(names)
with (run / "tests.log").open("w", encoding="utf-8") as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
report = {"scope": "Selected tests only; not a full regression suite", "tests_run": result.testsRun,
          "successful": result.wasSuccessful(), "failures": [str(t) for t, _ in result.failures],
          "errors": [str(t) for t, _ in result.errors], "skipped": [str(t) for t, _ in result.skipped],
          "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for directory in ["src/pmda", "tests", "scripts"] for p in sorted((ROOT / directory).glob("*.py"))}}
(run / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k != "sources"}, indent=2))
print(run)
raise SystemExit(not result.wasSuccessful())
