"""Preserve the stopped workspace, restore its backup to the same location, verify."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from backup_portal import backup, restore, stopped, ROOT
from pmda.store import Store

stopped()
source = (ROOT / "runtime/portal").resolve()
preserved = (ROOT / "runtime" / ("portal-before-restore-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))).resolve()
if source.parent != (ROOT / "runtime").resolve() or preserved.parent != source.parent or preserved.exists():
    raise ValueError("Unsafe restore drill paths")
original_store = Store(source / "campaigns")
heads = {r["id"]: original_store.verify_history(r["id"]) for r in original_store.list_campaigns(include_archived=True)}
archive = backup(source)
source.rename(preserved)
try:
    restore(archive, source)
    if (preserved / "LOCAL_ACCESS.txt").exists():
        shutil.copyfile(preserved / "LOCAL_ACCESS.txt", source / "LOCAL_ACCESS.txt")
    with sqlite3.connect(source / "portal.sqlite3") as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    db.close()
    recovered = Store(source / "campaigns")
    for cid, head in heads.items():
        assert recovered.verify_history(cid) == head
    report = {"status":"passed","backup":str(archive),"preserved_original":str(preserved),"campaigns_verified":len(heads),"sessions_invalidated":True,"automatic_jobs_launched":0}
except Exception:
    # Keep both copies for inspection; never silently destroy either version.
    raise RuntimeError("Restore drill needs inspection. Original data is preserved at " + str(preserved))
(archive / "restore-drill.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
