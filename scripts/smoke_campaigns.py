"""User-authorized infrastructure tests with explicitly automated test approvals.

These are not scientist-reviewed pharma campaigns. Each run records that scope.
"""
import argparse
import os
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
import csv
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import time
from pmda.store import Store,digest
from pmda.execution import ExecutionService
from pmda.evaluation import evaluate

ROOT = Path(__file__).resolve().parents[1]


def save(path, data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding="utf-8")


def main(kind, cancel_after=None, timeout_seconds=300, use_mcp=False):
    run = ROOT / "runtime" / ("controlled-"+kind+"-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    store = Store(run, principal="automated-infrastructure-test")
    cid = store.create("User-authorized bounded infrastructure smoke test; approvals are automated test fixtures")
    base = run / cid
    inputs = base / "inputs"
    outputs = base / "outputs"
    inputs.mkdir()
    prior = inputs / "reinvent.prior"
    shutil.copyfile(ROOT / ("models/mol2mol_medium_similarity.prior" if kind=="mol2mol" else "models/reinvent_pubchem.prior"),prior)
    run_kind = "sampling" if kind=="mol2mol" else kind
    records = [prior]
    if kind=="mol2mol":
        seeds=inputs / "seeds.smi"
        seeds.write_text("CC(=O)Nc1ccccc1\n",encoding="utf-8")
        records.append(seeds)
    if kind == "transfer_learning":
        with (ROOT / "runtime/baseline-20261027T133115176071Z/sampling.csv").open() as stream:
            sampled = list(csv.DictReader(stream))
        from rdkit import Chem
        column = next(k for k in sampled[0] if k.lower() == "smiles")
        smiles = [r[column] for r in sampled if Chem.MolFromSmiles(r[column]) is not None][:32]
        training = inputs / "training.smi"
        training.write_text("\n".join(smiles)+"\n",encoding="utf-8")
        records.append(training)
    save(base / "inputs.json",{"schema_version":"1.0","artifacts":[{"path":str(p),"sha256":digest(p.read_bytes()),"size":p.stat().st_size} for p in records]})
    plan = {"objective":{"identifier":"infrastructure-smoke","description":"No potency claim; bounded engine validation",
        "mode":"infrastructure","budget":{"max_jobs":1,"max_seconds_per_job":timeout_seconds,"max_candidates":100}},
        "rationale":"Automated test approvals under development authorization", "strategy":{"run_type":run_kind,"model_sha256":digest(prior.read_bytes())}}
    score = {"purpose":"infrastructure","components":[{"name":"QED","direction":"maximize","weight":1}]}
    save(base / "plan.json",plan)
    save(base / "score.json",score)
    q = lambda p: json.dumps(str(p))
    config = f'run_type="{run_kind}"\ndevice="cpu"\nseed=42\njson_out_config={q(outputs / "executed.json")}\n'
    if kind=="mol2mol":
        config += f'[parameters]\nmodel_file={q(prior)}\nsmiles_file={q(seeds)}\noutput_file={q(outputs / "samples.csv")}\nnum_smiles=8\nunique_molecules=false\nrandomize_smiles=true\nsample_strategy="multinomial"\ntemperature=1.0\n'
    elif kind == "sampling":
        config += f'[parameters]\nmodel_file={q(prior)}\noutput_file={q(outputs / "samples.csv")}\nnum_smiles=32\nunique_molecules=false\nrandomize_smiles=true\n'
    elif kind == "transfer_learning":
        config += f'[parameters]\ninput_model_file={q(prior)}\nsmiles_file={q(training)}\noutput_model_file={q(outputs / "trained.model")}\nnum_epochs=1\nsave_every_n_epochs=1\nbatch_size=16\nnum_refs=0\nsample_batch_size=100\ntb_isim=false\n'
    else:
        config += f'[parameters]\nprior_file={q(prior)}\nagent_file={q(prior)}\nsummary_csv_prefix={q(outputs / "rl")}\nbatch_size=16\nuse_checkpoint=false\npurge_memories=false\nrandomize_smiles=true\ntb_isim=false\n'
        config += '[learning_strategy]\ntype="dap"\nsigma=128\nrate=0.0001\n'
        config += f'[[stage]]\nchkpt_file={q(outputs / "rl.chkpt")}\ntermination="simple"\nmax_score=1.0\nmin_steps=2\nmax_steps=2\n[stage.scoring]\ntype="geometric_mean"\n[[stage.scoring.component]]\n[stage.scoring.component.QED]\n[[stage.scoring.component.QED.endpoint]]\nname="QED"\nweight=1.0\n'
    if use_mcp:
        import asyncio,sys
        from pmda.mcp_client import session
        from pmda.engine_adapter import propose,discover
        plan["strategy"]["seed"]=None
        save(base / "plan.json",plan)
        async def preview():
            async with session(sys.executable,ROOT / "vendor/solitarius-mcp/server.py",base,base / "mcp.log") as client:
                save(base / "mcp-capabilities.json",await discover(client))
                args={"workdir":base.as_posix()}
                if run_kind=="sampling":
                    args.update(model_file=prior.as_posix(),output_file=(outputs / "samples.csv").as_posix(),
                        num_smiles=8 if kind=="mol2mol" else 32,unique_molecules=False,randomize_smiles=True)
                    if kind=="mol2mol":
                        args.update(generator="mol2mol",smiles_file=seeds.as_posix(),sample_strategy="multinomial",temperature=1.0)
                elif kind=="transfer_learning":
                    args.update(input_model_file=prior.as_posix(),smiles_file=training.as_posix(),
                        output_model_file=(outputs / "trained.model").as_posix(),num_epochs=1,batch_size=16,save_every_n_epochs=1,
                        tb_logdir=(outputs / "tb").as_posix(),standardize_smiles=False)
                else:
                    args.update(prior_file=prior.as_posix(),agent_file=prior.as_posix(),output_prefix=(outputs / "rl").as_posix(),
                        batch_size=16,tb_logdir=(outputs / "tb").as_posix(),stages=[{"chkpt_file":(outputs / "rl.chkpt").as_posix(),
                        "max_score":1.0,"min_steps":2,"max_steps":2,"scoring":{"aggregation":"geometric_mean", "components":[{"component_type":"QED","name":"QED","weight":1.0}]}}])
                return await propose(client,run_kind,args,base,plan["objective"]["budget"])
        proposal=asyncio.run(preview())
        config=Path(proposal["path"]).read_bytes().decode("utf-8")
    (base / "config.toml").write_bytes(config.encode("utf-8"))
    def move(state):
        store.transition(cid,state,store.get(cid)["revision"])
    def approve(file):
        return store.approve(cid,file,digest((base / file).read_bytes()),store.principal)
    move("PLANNING"); move("AWAITING_PLAN_APPROVAL"); approve("plan.json")
    move("AWAITING_SCORE_APPROVAL"); approve("score.json")
    move("AWAITING_LAUNCH_APPROVAL"); aid = approve("config.toml")
    service = ExecutionService(store)
    launched = service.launch(cid,aid)
    print(json.dumps({"root":str(run),"campaign":cid,**launched}),flush=True)
    deadline = time.monotonic()+360
    started = time.monotonic()
    cancel_requested = False
    while time.monotonic()<deadline:
        if cancel_after is not None and not cancel_requested and time.monotonic()-started>=cancel_after:
            service.cancel(launched["job_id"])
            cancel_requested=True
        job = service.reconcile(launched["job_id"])
        if job["status"] in {"succeeded","failed","cancelled","timed_out","ambiguous"}:
            break
        time.sleep(1)
    else:
        service.cancel(launched["job_id"])
        raise RuntimeError("Smoke monitor deadline exceeded")
    result = json.loads(job["result"])
    if use_mcp:
        expected_bytes=(base / "proposed.toml").read_bytes()
        actual_bytes=(base / "jobs" / job["id"] / "approved.toml").read_bytes()
        if expected_bytes!=actual_bytes:
            raise RuntimeError("MCP preview and executed bytes differ")
        save(base / "config-identity.json",{"exact_bytes":True,"sha256":digest(actual_bytes)})
    expected = "cancelled" if cancel_after is not None else "timed_out" if timeout_seconds<10 else "succeeded"
    if expected!="succeeded" and job["status"]==expected:
        store.verify_history(cid)
        save(run / "summary.json",{"status":"passed","kind":kind,"expected":expected,"campaign":cid,"job":job["id"],"scope":"failure-path integration test"})
        print(f"PASS {expected}: {run}",flush=True)
        return
    if job["status"] != "succeeded":
        print(json.dumps(result,indent=2),flush=True)
        raise RuntimeError("Engine smoke failed")
    if run_kind == "sampling":
        with (outputs / "samples.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        col = next(k for k in rows[0] if k.lower()=="smiles")
        if len(rows)!=(8 if kind=="mol2mol" else 32):
            raise RuntimeError("Unexpected number of samples")
        save(outputs / "evaluation.json",evaluate([r[col] for r in rows]))
    artifacts = result["artifacts"]
    save(base / "evidence.json",{"campaign":cid,"job_id":job["id"],"results":{"artifacts":artifacts},
        "evaluator_version":"infrastructure-v1","qualified":False,"limitations":["Automated development smoke; not a target-specific pharma campaign"]})
    save(base / "analysis.json",{"decision":"complete","evidence_sha256":digest((base / "evidence.json").read_bytes()),"rationale":"Bounded engine execution succeeded; no scientific success claim"})
    move("ANALYSING"); move("COMPLETED")
    store.verify_history(cid)
    store.render(cid)
    save(run / "summary.json",{"status":"passed","kind":kind,"campaign":cid,"job":job["id"],"scope":"automated infrastructure test","state":store.get(cid)["state"]})
    print(f"PASS: {run}",flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("kind",choices=["sampling","mol2mol","transfer_learning","staged_learning"])
    parser.add_argument("--cancel-after",type=float)
    parser.add_argument("--timeout-seconds",type=int,default=300)
    parser.add_argument("--mcp",action="store_true")
    args=parser.parse_args()
    main(args.kind,args.cancel_after,args.timeout_seconds,args.mcp)
