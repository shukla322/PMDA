"""Bounded, user-authorized Stage 7 development campaign with real local agents.

Approvals record delegated development authorization, not independent scientific
review. No external chemistry experiments, purchases or cloud calls are made.
"""
import os
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time
from pmda.agents import LocalProvider, propose
from pmda.local_runtime import local_server
from pmda.registry import Registry
from pmda.reward import ConservativeReward
from pmda.evaluation import export_evaluation
from pmda.execution import ExecutionService, validate_config
from pmda.store import Store, digest

ROOT = Path(__file__).resolve().parents[1]
AUTHORIZATION = "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff."


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")


def artifact(path):
    return {"path": str(path), "sha256": digest(path.read_bytes()), "size": path.stat().st_size}


def choose_lead(training, reward):
    from rdkit import Chem
    from rdkit.Chem import Descriptors, QED
    motif = Chem.MolFromSmarts(reward.recipe.required_smarts)
    candidates = []
    for row in training:
        mol = Chem.MolFromSmiles(row["smiles"])
        if row["pic50"] >= 7 and mol.HasSubstructMatch(motif) and Descriptors.MolWt(mol) <= 500:
            candidates.append((QED.qed(mol), row))
    for _, row in sorted(candidates, key=lambda item: (-item[0], item[1]["smiles"])):
        evaluated = reward.score([row["smiles"]])["rows"][0]
        if evaluated["passes_configured_gates"]:
            return row, evaluated
    raise ValueError("No training-only lead meets the frozen policy")


def portfolio(result, references):
    from rdkit import Chem, DataStructs
    from rdkit.Chem import rdFingerprintGenerator
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    known = {Chem.MolToSmiles(Chem.MolFromSmiles(s)) for s in references}
    selected, fingerprints = [], []
    for row in sorted(result["rows"], key=lambda r: (-r["reward"], r.get("canonical_smiles", ""))):
        row["novel_to_training"] = row.get("canonical_smiles") not in known if row["valid"] else False
        if not row.get("passes_configured_gates", False):
            continue
        if not row["novel_to_training"] or row["activity"].get("lower", -100) < 6:
            continue
        fp = gen.GetFingerprint(Chem.MolFromSmiles(row["canonical_smiles"]))
        if fingerprints and max(DataStructs.BulkTanimotoSimilarity(fp, fingerprints)) > .85:
            continue
        selected.append(row)
        fingerprints.append(fp)
        if len(selected) == 10:
            break
    return selected


def main(seed=42, arm="full", counts=(48, 32, 32), destination=None):
    from contextlib import nullcontext
    from pmda.agents import SCHEMAS, required_rationale, expected_analysis
    if arm not in {"full", "fixed", "prior", "mol2mol", "no_feedback"}:
        raise ValueError("Unknown benchmark arm")
    total = sum(counts)
    single = arm in {"prior", "mol2mol", "no_feedback"}
    iterations = 1 if single else 3
    live_roles = {"planner", "executor"} if arm == "no_feedback" else set(SCHEMAS) if arm == "full" else set()
    def advise(role, context, provider, archive):
        if role in live_roles:
            return propose(role, context, provider, archive)
        fields = {"rationale": required_rationale(role, context)}
        if role == "planner":
            fields.update(action="propose", target=context["target"], predictor=context["predictor"], missing_information=[])
        elif role == "formulator":
            fields.update(component=context["component"], predictor=context["predictor"])
        elif role == "executor":
            fields.update(action="preview", run_type=context["run_type"])
        else:
            fields.update(zip(("decision", "diagnosis"), expected_analysis(context)))
        result = SCHEMAS[role](**fields)
        save(archive / "deterministic-baseline.json", {"not_an_llm_call": True, "proposal": result.model_dump()})
        return result
    run = Path(destination) if destination else ROOT / "runtime" / ("egfr-campaign-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    store = Store(run)
    cid = store.create("EGFR wild-type analogue prioritization: research predictions only")
    base = run / cid
    inputs, outputs = base / "inputs", base / "outputs"
    inputs.mkdir(); outputs.mkdir()
    registry = Registry(ROOT)
    predictor = registry.optimization_predictor("EGFR-rf-v1")
    dataset = registry.load("datasets", "EGFR-curated-v1")
    prior = inputs / "mol2mol.prior"
    shutil.copyfile(ROOT / ("models/reinvent_pubchem.prior" if arm == "prior" else "models/mol2mol_medium_similarity.prior"), prior)
    model = inputs / "model.json"
    shutil.copyfile(ROOT / predictor.artifact.path, model)
    # Reconstruct split membership from frozen dataset; never pick a lead using test labels.
    from pmda.predictor import split
    rows = json.loads((ROOT / dataset.artifact.path).read_bytes())
    training = [rows[int(i)] for i in split(rows)["train"]]
    recipe = {"model_sha256": predictor.artifact.sha256, "required_smarts": "c1ncnc2ccccc12"}
    reward = ConservativeReward(inputs, recipe)
    recipe = reward.recipe.model_dump()
    recipe_file = inputs / "reward.json"
    save(recipe_file, recipe)
    lead, lead_evidence = choose_lead(training, reward)
    seeds = inputs / "lead.smi"
    seeds.write_text(lead["smiles"] + "\n", encoding="utf-8")
    save(inputs / "training-reference.json", [r["smiles"] for r in training])
    save(base / "lead-selection.json", {"rule": "Training only: measured pIC50 >=7, quinazoline motif, MW<=500, reward gates; highest QED, lexicographic tie break", "dataset_sha256": dataset.artifact.sha256, "lead": lead, "evidence": lead_evidence})
    criteria = {"minimum_portfolio_size": 3, "minimum_predicted_lower_pic50": 6,
                "maximum_pairwise_tanimoto": .85, "novelty_reference": "training partition only",
                "max_adaptive_iterations": iterations - 1, "max_candidates": total,
                "claim": "Computational prioritization; no demonstrated potency, selectivity, safety or synthesis feasibility"}
    save(inputs / "criteria.json", criteria)
    save(base / "authorization.json", {"scope": AUTHORIZATION, "principal": store.principal})
    budget = {"max_jobs": iterations, "max_seconds_per_job": 600, "max_candidates": total}
    records = [prior, model, recipe_file, seeds, inputs / "training-reference.json", inputs / "criteria.json"]
    comparison = []
    service = ExecutionService(store)
    def move(state):
        store.transition(cid, state, store.get(cid)["revision"])
    def approve(path):
        return store.approve(cid, str(path.relative_to(base)), digest(path.read_bytes()), store.principal, comments=AUTHORIZATION)
    save(run / "status.json", {"campaign": cid, "state": "preparing", "root": str(run)})
    print("CAMPAIGN", str(base), flush=True)
    with local_server(base / "inference") if live_roles else nullcontext(None) as url:
        provider = LocalProvider(url) if url else None
        for iteration in range(iterations):
            folder = base / f"iteration-{iteration}"
            folder.mkdir()
            agents = folder / "agents"
            if iteration:
                move("AWAITING_REVISION_APPROVAL")
                save(folder / "revision.json", {"reason": "Previous portfolio did not meet frozen criteria", "changes": ["Bounded two-step Mol2Mol activity RL" if iteration == 1 else "Independent sampling from the resulting checkpoint; same science policy"]})
                approve(folder / "revision.json")
            else:
                move("PLANNING")
            kind = "staged_learning" if iteration == 1 else "sampling"
            generation_model = prior
            if iteration == 2:
                generation_model = inputs / "optimized.prior"
                shutil.copyfile(outputs / "iteration-1/optimized.chkpt", generation_model)
                records.append(generation_model)
            save(base / "inputs.json", {"artifacts": [artifact(p) for p in records]})
            planner = advise("planner", {"objective": "Prioritize EGFR wild-type analogues under frozen criteria", "target": predictor.target, "predictor": predictor.identifier, "missing_information": []}, provider, agents / "planner")
            plan = {"objective": {"identifier": "egfr-analogue-v1", "description": "Research-only EGFR analogue prioritization", "target": predictor.target, "mode": "research", "budget": budget},
                    "rationale": planner.rationale, "strategy": {"run_type": kind, "model_sha256": digest(generation_model.read_bytes()), "seed": seed}}
            save(folder / "plan.json", plan)
            move("AWAITING_PLAN_APPROVAL"); approve(folder / "plan.json")
            advise("formulator", {"predictor": predictor.identifier, "component": "conservative_activity_v1", "qualification": predictor.eligible_for_optimization}, provider, agents / "formulator")
            score = {"purpose": "research", "components": [{"name": "activity", "direction": "maximize", "weight": 1., "predictor_id": predictor.identifier, "predictor_sha256": predictor.artifact.sha256, "recipe_sha256": digest(recipe_file.read_bytes())}]}
            save(folder / "score.json", score)
            move("AWAITING_SCORE_APPROVAL"); approve(folder / "score.json")
            out = outputs / f"iteration-{iteration}"
            out.mkdir()
            q = lambda path: json.dumps(str(path))
            config = f'run_type="{kind}"\ndevice="cpu"\nseed={seed}\njson_out_config={q(out / "executed.json")}\n'
            if kind == "sampling":
                count = total if single else counts[iteration]
                config += f'[parameters]\nmodel_file={q(generation_model)}\nsmiles_file={q(seeds)}\noutput_file={q(out / "samples.csv")}\nnum_smiles={count}\nunique_molecules=false\nrandomize_smiles=true\nsample_strategy="multinomial"\ntemperature=1.0\n'
            else:
                config += f'[parameters]\nprior_file={q(prior)}\nagent_file={q(prior)}\nsmiles_file={q(seeds)}\nsummary_csv_prefix={q(out / "rl")}\nbatch_size=16\nuse_checkpoint=false\npurge_memories=false\nrandomize_smiles=true\ntb_isim=false\n'
                config = config.replace('batch_size=16', 'batch_size=' + str(counts[1] // 2))
                config += '[learning_strategy]\ntype="dap"\nsigma=64\nrate=0.0001\n'
                config += f'[[stage]]\nchkpt_file={q(out / "optimized.chkpt")}\ntermination="simple"\nmax_score=1.0\nmin_steps=2\nmax_steps=2\n[stage.scoring]\ntype="geometric_mean"\n[[stage.scoring.component]]\n[stage.scoring.component.PMDAActivity]\n[[stage.scoring.component.PMDAActivity.endpoint]]\nname="Conservative EGFR activity"\nweight=1.0\n[stage.scoring.component.PMDAActivity.endpoint.params]\nmodel_file={q(model)}\nrecipe_file={q(recipe_file)}\n'
            if arm == "prior":
                config = config.replace('smiles_file=' + q(seeds) + '\n', '')
            config_file = folder / "config.toml"
            config_file.write_bytes(config.encode())
            validate_config(config_file.read_bytes(), base, budget)
            advise("executor", {"run_type": kind, "approved": True, "config_sha256": digest(config_file.read_bytes())}, provider, agents / "executor")
            move("AWAITING_LAUNCH_APPROVAL")
            launch = service.launch(cid, approve(config_file))
            print("LAUNCH", iteration, kind, launch["job_id"], flush=True)
            deadline = time.monotonic() + 660
            while time.monotonic() < deadline:
                job = service.reconcile(launch["job_id"])
                if job["status"] in {"succeeded", "failed", "cancelled", "timed_out", "ambiguous"}:
                    break
                time.sleep(1)
            else:
                service.cancel(launch["job_id"])
                raise RuntimeError("Monitor deadline; cancellation requested")
            if job["status"] != "succeeded":
                save(run / "status.json", {"campaign": cid, "state": job["status"], "iteration": iteration})
                raise RuntimeError("Engine did not succeed: " + str(job["result"]))
            source = out / ("samples.csv" if kind == "sampling" else "rl_1.csv")
            with source.open(encoding="utf-8") as stream:
                sampled = list(csv.DictReader(stream))
            column = next(k for k in sampled[0] if k.lower() == "smiles")
            evaluated = reward.score([row[column] for row in sampled])
            selected = portfolio(evaluated, [r["smiles"] for r in training])
            export_evaluation(evaluated, folder / "evaluation")
            save(folder / "portfolio.json", selected)
            met = len(selected) >= criteria["minimum_portfolio_size"]
            # RL trajectory rows are exploratory; only independent sampling can close the campaign.
            met = met and kind == "sampling"
            comparison.append({"iteration": iteration, "run_type": kind, "samples": len(sampled), "portfolio_size": len(selected), "criteria_met": met, "mean_reward": sum(r["reward"] for r in evaluated["rows"]) / len(sampled)})
            analysis = advise("analyser", {"qualified": True, "execution_succeeded": True, "criteria_met": met, "remaining_iterations": iterations - 1 - iteration, "candidate_count": len(selected)}, provider, agents / "analyser")
            save(folder / "agent-analysis.json", analysis.model_dump())
            move("ANALYSING")
            print("EVALUATED", comparison[-1], flush=True)
            if (met and arm != "fixed") or iteration == iterations - 1:
                engine_result = json.loads(job["result"])
                evidence_files = [folder / "evaluation/evaluation.json", folder / "evaluation/candidates.parquet", folder / "portfolio.json", folder / "agent-analysis.json"]
                save(base / "evidence.json", {"campaign": cid, "job_id": job["id"], "results": {"artifacts": engine_result["artifacts"] + [artifact(p) for p in evidence_files]}, "evaluator_version": "conservative-activity-v1", "qualified": met, "limitations": predictor.limitations + [criteria["claim"], "Novelty checked against training partition only; no patent or global novelty claim", AUTHORIZATION]})
                save(base / "analysis.json", {"decision": "complete" if met else "stop", "evidence_sha256": digest((base / "evidence.json").read_bytes()), "rationale": analysis.rationale})
                move("COMPLETED" if met else "FAILED")
                save(base / "final-portfolio.json", selected)
                break
    save(base / "iteration-comparison.json", comparison)
    store.verify_history(cid)
    store.render(cid)
    save(run / "summary.json", {"campaign": cid, "workflow_executed": True, "scientific_criteria_met": met, "state": store.get(cid)["state"], "iterations": comparison, "authorization": AUTHORIZATION})
    save(run / "status.json", {"campaign": cid, "state": store.get(cid)["state"]})
    print("FINISHED", str(run), "criteria_met", met, flush=True)
    return run


if __name__ == "__main__":
    main()
