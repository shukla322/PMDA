"""Persistent local supervisor. Survives the initiating CLI exiting."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import psutil
from .store import Store, digest
from .execution import validate_config


def write_json(path,data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,indent=2),encoding="utf-8")
    tmp.replace(path)


def stop_tree(proc):
    try:
        root = psutil.Process(proc.pid)
        children = root.children(recursive=True)
        for child in children:
            child.kill()
        root.kill()
        psutil.wait_procs(children+[root],timeout=5)
    except psutil.NoSuchProcess:
        pass
    proc.wait(timeout=10)


def run(root,jid):
    start = time.monotonic()
    store = Store(root)
    job = store.job(jid)
    cid = job["campaign"]
    work = store.artifact(cid,"jobs/"+jid)
    campaign = store.root / cid
    config_path = work / "approved.toml"
    result = {"job_id":jid,"config_sha256":job["config_hash"],"status":"failed","artifacts":[]}
    proc = None
    with store.transaction() as db:
        changed = db.execute("UPDATE jobs SET status='starting',pid=? WHERE id=? AND status='reserved'",(os.getpid(),jid)).rowcount
        if changed != 1:
            raise RuntimeError("Job already claimed; refusing duplicate execution")
    write_json(work / "supervisor.json",{"pid":os.getpid(),"created":psutil.Process().create_time()})
    try:
        content = config_path.read_bytes()
        if digest(content) != job["config_hash"]:
            raise ValueError("Reserved config checksum mismatch")
        budget = json.loads(store.get(cid)["budget"])
        config = validate_config(content,campaign,budget)
        (campaign / "outputs").mkdir(exist_ok=True)
        (work / "tmp").mkdir(exist_ok=True)
        env = os.environ.copy()
        env.update(MPLCONFIGDIR=str(work / "matplotlib"), TEMP=str(work / "tmp"),TMP=str(work / "tmp"))
        with (work / "engine.log").open("wb") as log:
            proc = subprocess.Popen([sys.executable,"-m","reinvent.Reinvent",str(config_path)],
                cwd=campaign,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            write_json(work / "engine.json",{"pid":proc.pid,"created":psutil.Process(proc.pid).create_time()})
            with store.transaction() as db:
                db.execute("UPDATE jobs SET status='running' WHERE id=?",(jid,))
                store.event(db,cid,"engine_started",{"job_id":jid,"pid":proc.pid})
            while proc.poll() is None:
                if (work / "cancel.request").exists():
                    stop_tree(proc)
                    result.update(status="cancelled",error_code="OWNER_CANCELLED")
                    break
                if time.monotonic()-start > budget["max_seconds_per_job"]:
                    stop_tree(proc)
                    result.update(status="timed_out",error_code="WALL_TIME_BUDGET")
                    break
                time.sleep(.2)
            else:
                result.update(status="succeeded" if proc.returncode == 0 else "failed",exit_code=proc.returncode)
                if proc.returncode != 0:
                    result["error_code"] = "ENGINE_EXIT"
        outputs = [p for p in (campaign / "outputs").rglob("*") if p.is_file()]
        primary = [Path(config["parameters"][key]) for key in ("output_file","output_model_file") if key in config["parameters"]]
        primary += [Path(stage["chkpt_file"]) for stage in config.get("stage",[])]
        if result["status"] == "succeeded" and (not primary or any(not p.is_file() or not p.stat().st_size for p in primary)):
            result.update(status="failed",error_code="MISSING_OUTPUTS")
        outputs += [p for p in (work / "engine.log",config_path) if p.exists()]
        for path in outputs:
            result["artifacts"].append({"path":str(path.relative_to(campaign)),"sha256":digest(path.read_bytes()),"size":path.stat().st_size})
        result["elapsed_seconds"] = time.monotonic()-start
    except Exception as exc:
        if proc and proc.poll() is None:
            stop_tree(proc)
        result.update(status="failed",error_code="SUPERVISOR_ERROR",message=f"{type(exc).__name__}: {exc}")
    write_json(work / "result.json",result)
    store.finish_job(jid,result["status"],result)


if __name__ == "__main__":
    run(sys.argv[1],sys.argv[2])
