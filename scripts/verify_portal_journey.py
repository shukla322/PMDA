"""Real HTTP workflow smoke, not a browser test or independent scientific review."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
record = ROOT / "runtime" / ("portal-journey-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
record.mkdir()
access = (ROOT / "runtime/portal/LOCAL_ACCESS.txt").read_text(encoding="utf-8")
credentials = dict(line.split(": ",1) for line in access.splitlines() if ": " in line)
session = requests.Session()
session.trust_env = False
origin = "http://127.0.0.1:8765"
steps=[]


def api(path, method="GET", body=None):
    response = session.request(method, origin + "/api/v1" + path, json=body, timeout=30)
    if not response.ok:
        raise RuntimeError(f"{method} {path}: {response.status_code} {response.text[:400]}")
    return response.json()


try:
    signed = api("/login","POST",dict(username=credentials["Username"],password=credentials["Password"]))
    session.headers["X-CSRF-Token"] = signed["csrf"]
    health = api("/health")
    created = api("/projects/workspace/campaigns","POST",dict(objective="Automated local release verification: four-candidate EGFR workflow; no medicinal-chemist signoff",lead=health["default_lead"],candidates=4,seed=43))
    cid=created["id"]
    base=f"/projects/workspace/campaigns/{cid}"
    previous=None
    for _ in range(600):
        detail=api(base)
        state=detail["campaign"]["state"]
        busy=any(o["status"] in {"queued","running"} for o in detail["operations"])
        if state!=previous:
            steps.append(dict(state=state,time=datetime.now(timezone.utc).isoformat()))
            print("JOURNEY",state,flush=True)
            previous=state
        failed=[o for o in detail["operations"] if o["status"] in {"failed","interrupted"}]
        if failed:
            raise RuntimeError("Preparation failed: "+failed[0]["error"])
        if state.startswith("AWAITING_"):
            review=api(base+"/review")
            api(base+"/approve","POST",dict(sha256=review["sha256"],revision=review["revision"],comments="Automated verification under owner-authorized local development scope; not independent scientific approval",confirmed=True))
        elif state in {"FORMULATING","CONFIGURING","EVALUATING"} and not busy:
            api(base+"/advance","POST",{})
        elif state=="QUEUED":
            api(base+"/launch","POST",{})
        elif state in {"COMPLETED","FAILED","CANCELLED"}:
            break
        time.sleep(2)
    else:
        raise RuntimeError("Workflow monitor deadline; inspect recorded operations and job before retrying")
    candidates=api(base+"/candidates")
    assert candidates["total"]==4, "Expected four evaluated rows"
    roles=api(base+"/orchestration")["roles"]
    assert len(roles)==4 and all(r["accepted"] for r in roles)
    assert len(detail["approvals"])==3
    assert detail["jobs"][-1]["status"]=="succeeded"
    files=api(base+"/files")
    assert any(f["path"]=="REPORT.md" for f in files)
    response=session.get(origin+"/api/v1"+base+"/download",params={"path":"REPORT.md"},timeout=10)
    assert response.ok and "EGFR campaign report" in response.text
    valid=next((r for r in candidates["rows"] if r["valid"]),None)
    if valid:
        response=session.get(origin+"/api/v1"+base+"/molecule/"+str(valid["row"]),timeout=10)
        assert response.ok and "<svg" in response.text
    result=dict(status="passed",scope="Real HTTP API journey with local agents and REINVENT; not a browser automation claim",campaign=cid,state=state,evaluated_rows=candidates["total"],steps=steps)
except Exception as exc:
    result=dict(status="failed",error=str(exc),steps=steps)
finally:
    (record / "result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    try:
        api("/logout","POST",{})
    except Exception:
        pass
    session.close()
print(json.dumps(result,indent=2),flush=True)
print(record,flush=True)
raise SystemExit(result["status"]!="passed")
