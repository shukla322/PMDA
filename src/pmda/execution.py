"""Bounded execution of reviewed TOML; MCP builds proposals, this service launches.

Supported inputs are local trusted assets. Arbitrary score plugins, remote
responders, external config includes and shell commands are intentionally rejected.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from .contracts import PolicyError
from .store import digest

INPUT_KEYS = {"model_file", "input_model_file", "smiles_file", "validation_smiles_file", "prior_file", "agent_file"}
OUTPUT_KEYS = {"output_file", "output_model_file", "summary_csv_prefix"}
PARAMETERS = {
    "sampling": {"model_file", "smiles_file", "output_file", "num_smiles", "unique_molecules", "randomize_smiles", "sample_strategy", "temperature"},
    "transfer_learning": {"input_model_file", "smiles_file", "validation_smiles_file", "output_model_file", "num_epochs", "save_every_n_epochs", "batch_size", "num_refs", "sample_batch_size", "tb_isim", "standardize_smiles"},
    "staged_learning": {"prior_file", "agent_file", "smiles_file", "summary_csv_prefix", "batch_size", "use_checkpoint", "purge_memories", "randomize_smiles", "tb_isim"}}


def candidate_count(config):
    params=config["parameters"]
    if config["run_type"]=="sampling":
        seeds=1
        if params.get("smiles_file"):
            seeds=sum(bool(line.strip()) for line in Path(params["smiles_file"]).read_text(encoding="utf-8").splitlines())
        return params["num_smiles"]*seeds
    if config["run_type"]=="transfer_learning":
        return params.get("sample_batch_size",100)*params["num_epochs"]
    return sum(stage["max_steps"]*params["batch_size"] for stage in config["stage"])


def contained(path, campaign):
    path = Path(path)
    if not path.is_absolute() or not path.resolve().is_relative_to(campaign.resolve()):
        raise PolicyError("Engine paths must be absolute and inside the campaign")
    return path.resolve()


def validate_config(content, campaign, budget):
    from reinvent.validation import ReinventConfig
    campaign = Path(campaign).resolve()
    config = tomllib.loads(content.decode("utf-8"))
    if set(config) - {"run_type", "device", "seed", "parameters", "json_out_config", "tb_logdir", "learning_strategy", "stage", "diversity_filter"}:
        raise PolicyError("Unsupported configuration key")
    kind = config.get("run_type")
    if kind not in PARAMETERS or config.get("device") != "cpu":
        raise PolicyError("Only bounded supported CPU run types are enabled")
    params = config.get("parameters", {})
    if set(params) - PARAMETERS[kind]:
        raise PolicyError("Unsupported engine parameter")
    from .schemas import ArtifactManifest
    manifest = ArtifactManifest.model_validate_json((campaign / "inputs.json").read_bytes()).model_dump()
    inputs = {}
    for item in manifest["artifacts"]:
        path = contained(item["path"],campaign)
        if not path.is_file() or path.stat().st_size != item["size"] or digest(path.read_bytes()) != item["sha256"]:
            raise PolicyError("Input integrity failure")
        inputs[str(path)] = item
    for key,value in params.items():
        if key in INPUT_KEYS:
            path = contained(value,campaign)
            if str(path) not in inputs:
                raise PolicyError("Unmanifested model/data input")
        if key in OUTPUT_KEYS:
            path = contained(value,campaign)
            if not path.is_relative_to(campaign / "outputs"):
                raise PolicyError("Engine outputs must stay in campaign/outputs")
            if path.exists() or (key=="summary_csv_prefix" and list(path.parent.glob(path.name+"*"))):
                raise PolicyError("Output already exists; use a fresh iteration path")
    for key in ("json_out_config", "tb_logdir"):
        if key in config and not contained(config[key],campaign).is_relative_to(campaign / "outputs"):
            raise PolicyError("Output escape")
        if key in config and Path(config[key]).exists():
            raise PolicyError("Configuration/log output already exists; use a fresh iteration path")
    if kind == "sampling":
        count = params.get("num_smiles", 0)
    elif kind == "transfer_learning":
        epochs = params.get("num_epochs",0)
        if not 1 <= epochs <= 3:
            raise PolicyError("Transfer learning epoch budget exceeded")
        count = params.get("sample_batch_size",100) * epochs
        if not 1 <= params.get("batch_size",0) <= 64:
            raise PolicyError("Invalid transfer learning batch size")
    else:
        diversity=config.get("diversity_filter",{})
        if diversity and (set(diversity)-{"type","bucket_size","minscore","minsimilarity","penalty_multiplier"} or diversity.get("type") not in {"IdenticalMurckoScaffold","IdenticalTopologicalScaffold","ScaffoldSimilarity","PenalizeSameSmiles"}):
            raise PolicyError("Unsupported diversity filter")
        stages = config.get("stage", [])
        if not 1 <= len(stages) <= 3:
            raise PolicyError("Invalid stage count")
        count = 0
        if set(config.get("learning_strategy",{})) - {"type","sigma","rate"}:
            raise PolicyError("Unsupported learning strategy fields")
        for stage in stages:
            if set(stage) - {"chkpt_file", "termination", "max_score", "min_steps", "max_steps", "scoring"}:
                raise PolicyError("Unsupported learning stage")
            if not contained(stage["chkpt_file"],campaign).is_relative_to(campaign / "outputs"):
                raise PolicyError("Checkpoint escape")
            if Path(stage["chkpt_file"]).exists():
                raise PolicyError("Checkpoint already exists; use a fresh iteration path")
            if not 1 <= stage.get("min_steps",0) <= stage.get("max_steps",0) <= 10:
                raise PolicyError("Learning step budget exceeded")
            count += stage["max_steps"] * params.get("batch_size",0)
            scoring = stage.get("scoring",{})
            if set(scoring) != {"type", "component"} or scoring["type"] not in {"geometric_mean", "arithmetic_mean"}:
                raise PolicyError("Unsupported scoring definition")
            for component in scoring["component"]:
                if set(component) == {"PMDAActivity"}:
                    specification = component["PMDAActivity"]
                    if set(specification) != {"endpoint"} or len(specification["endpoint"]) != 1:
                        raise PolicyError("Exactly one PMDA activity endpoint required")
                    endpoint = specification["endpoint"][0]
                    if set(endpoint) != {"name", "weight", "params"} or set(endpoint["params"]) != {"model_file", "recipe_file"}:
                        raise PolicyError("Unreviewed activity endpoint parameters")
                    for value in endpoint["params"].values():
                        if str(contained(value, campaign)) not in inputs:
                            raise PolicyError("Unmanifested reward input")
                    from .reward import load_reward
                    load_reward(**endpoint["params"])
                    continue
                if set(component) != {"QED"}:
                    raise PolicyError("Only reviewed QED and pinned PMDAActivity rewards are enabled")
                qed = component["QED"]
                if set(qed) != {"endpoint"}:
                    raise PolicyError("Unsupported QED settings")
                for endpoint in qed["endpoint"]:
                    if set(endpoint) - {"name","weight"}:
                        raise PolicyError("Arbitrary scoring parameters/transforms are disabled")
    if kind=="sampling":
        count=candidate_count(config)
    if not isinstance(count,int) or not 1 <= count <= budget["max_candidates"]:
        raise PolicyError("Candidate budget exceeded")
    ReinventConfig(**config)
    from reinvent.utils import extract_sections
    from reinvent.runmodes.samplers.validation import SamplingConfig
    from reinvent.runmodes.TL.validation import TLConfig
    from reinvent.runmodes.RL.validation import RLConfig
    {"sampling": SamplingConfig,"transfer_learning":TLConfig,"staged_learning":RLConfig}[kind](**extract_sections(config))
    return config


class ExecutionService:
    def __init__(self, store):
        self.store = store

    def launch(self, cid, approval):
        jid, config = self.store.reserve_launch(cid,approval)
        work = self.store.artifact(cid,"jobs/"+jid)
        work.mkdir(parents=True)
        (work / "approved.toml").write_bytes(config)
        env = os.environ.copy()
        env.pop("PYTHONPATH",None)
        env.pop("PYTHONHOME",None)
        env.update(OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", OPENBLAS_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1", PYTHONUTF8="1")
        # The child imports the installed BTP package; no shell and no generated code.
        try:
            with (work / "supervisor.log").open("wb") as log:
                proc = subprocess.Popen([sys.executable,"-m","pmda.worker",str(self.store.root),jid],
                    cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            return {"job_id":jid,"supervisor_pid":proc.pid}
        except OSError as exc:
            self.store.finish_job(jid,"failed",{"error_code":"SPAWN_FAILED","message":str(exc)})
            raise

    def reconcile(self, jid):
        import psutil
        job = self.store.job(jid)
        work = self.store.artifact(job["campaign"],"jobs/"+jid)
        result_path = work / "result.json"
        if result_path.exists():
            result = json.loads(result_path.read_bytes())
            if result.get("job_id") != jid or result.get("config_sha256") != job["config_hash"]:
                raise PolicyError("Result identity mismatch")
            for item in result.get("artifacts",[]):
                path = self.store.artifact(job["campaign"],item["path"])
                if not path.is_file() or path.stat().st_size != item["size"] or digest(path.read_bytes()) != item["sha256"]:
                    raise PolicyError("Output artifact mismatch")
            self.store.finish_job(jid,result["status"],result)
        elif job["status"] not in {"succeeded","failed","cancelled","timed_out"}:
            marker = work / "supervisor.json"
            alive = False
            if marker.exists():
                identity = json.loads(marker.read_bytes())
                try:
                    process = psutil.Process(identity["pid"])
                    alive = abs(process.create_time()-identity["created"]) < .01 and process.is_running()
                except psutil.Error:
                    pass
            # A just-spawned worker has a small startup window; no restart is ever automatic.
            from datetime import datetime,timezone
            age = (datetime.now(timezone.utc)-datetime.fromisoformat(job["created"])).total_seconds()
            if not alive and age > 30:
                self.store.finish_job(jid,"ambiguous",{"error_code":"SUPERVISOR_MISSING","action":"Inspect process markers; never relaunch automatically"})
        return self.store.job(jid)

    def cancel(self, jid):
        job = self.store.job(jid)
        if self.store.get(job["campaign"])["owner"] != self.store.principal:
            raise PolicyError("Only campaign owner may cancel")
        work = self.store.artifact(job["campaign"],"jobs/"+jid)
        if job["status"] in {"succeeded","failed","cancelled","timed_out"}:
            return job
        (work / "cancel.request").write_text("owner requested cancellation",encoding="utf-8")
        return self.reconcile(jid)

    def abandon_orphan(self, jid):
        """Owner acknowledges ambiguity; stop only identified engine processes.

        This never turns unknown work into success and never releases its budget.
        """
        import psutil
        job=self.reconcile(jid)
        if job["status"]!="ambiguous" or self.store.get(job["campaign"])["owner"]!=self.store.principal:
            raise PolicyError("Only owner may abandon a reconciled ambiguous job")
        work=self.store.artifact(job["campaign"],"jobs/"+jid)
        expected=str((work / "approved.toml").resolve())
        matched=[]
        marker=work / "engine.json"
        if marker.exists():
            identity=json.loads(marker.read_bytes())
            try:
                process=psutil.Process(identity["pid"])
                if abs(process.create_time()-identity["created"])<.01:
                    if expected not in process.cmdline():
                        raise PolicyError("Recorded process command changed; manual investigation required")
                    matched.append(process)
            except psutil.NoSuchProcess:
                pass
        # Also cover spawn-before-marker crashes. Match the full job-specific argv,
        # not a process name or a possibly reused PID.
        for process in psutil.process_iter(["pid","cmdline"]):
            if expected in (process.info["cmdline"] or []) and all(p.pid!=process.pid for p in matched):
                matched.append(process)
        killed=[]
        for process in matched:
            try:
                if expected not in process.cmdline():
                    raise PolicyError("Process identity changed during recovery")
                children=process.children(recursive=True)
                for child in children:
                    child.kill()
                process.kill()
                _,alive=psutil.wait_procs(children+[process],timeout=10)
                if alive:
                    raise PolicyError("Orphan process could not be stopped")
                killed.append(process.pid)
            except psutil.NoSuchProcess:
                pass
        result={"job_id":jid,"config_sha256":job["config_hash"],"status":"cancelled",
                "error_code":"OWNER_ABANDONED_AMBIGUOUS_JOB","stopped_pids":killed,"artifacts":[]}
        work.mkdir(parents=True,exist_ok=True)
        (work / "result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
        self.store.finish_job(jid,"cancelled",result)
        return self.store.job(jid)
