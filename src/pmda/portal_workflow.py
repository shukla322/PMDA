"""Reviewable portal workflow. Preparation never grants approval or launches jobs."""
import csv
import json
from pathlib import Path
import shutil
from .agents import LocalProvider, propose as model_propose, SCHEMAS, FIELDS, validate_semantics
from .local_runtime import local_server
from .registry import Registry
from .reward import ConservativeReward
from .evaluation import export_evaluation
from .execution import validate_config
from .store import digest

ROOT = Path(__file__).resolve().parents[2]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def artifact(path):
    return dict(path=str(path), sha256=digest(path.read_bytes()), size=path.stat().st_size)


def propose(role, context, provider, archive):
    """Reuse only validated matching evidence; retain failed attempts on retry."""
    if archive.exists():
        saved = json.loads((archive / "context.json").read_bytes()) if (archive / "context.json").exists() else {}
        if saved.get("context") == {key: context[key] for key in FIELDS[role]}:
            for path in sorted(archive.glob("attempt-*.json")):
                attempt = json.loads(path.read_bytes())
                if attempt.get("accepted"):
                    result = SCHEMAS[role].model_validate_json(attempt["text"])
                    validate_semantics(role, result, context)
                    return result
        index = 1
        while archive.with_name(archive.name + f"-retry-{index}").exists():
            index += 1
        archive = archive.with_name(archive.name + f"-retry-{index}")
    return model_propose(role, context, provider, archive)


def prepare(store, cid, lead, count, seed):
    from rdkit import Chem
    if Chem.MolFromSmiles(lead) is None or len(lead) > 1000:
        raise ValueError("Supply a valid lead SMILES")
    base = store.root / cid
    inputs = base / "inputs"
    if store.get(cid)["state"] not in {"DRAFT", "PLANNING"}:
        raise ValueError("Initial preparation cannot overwrite an approved campaign")
    inputs.mkdir(exist_ok=True)
    registry = Registry(ROOT)
    predictor = registry.optimization_predictor("EGFR-rf-v1")
    prior = inputs / "mol2mol.prior"
    shutil.copyfile(ROOT / "models/mol2mol_medium_similarity.prior", prior)
    shutil.copyfile(ROOT / predictor.artifact.path, inputs / "model.json")
    (inputs / "lead.smi").write_text(lead + "\n", encoding="utf-8")
    reward = ConservativeReward(inputs, dict(model_sha256=predictor.artifact.sha256, required_smarts="c1ncnc2ccccc12"))
    lead_result = reward.score([lead])["rows"][0]
    if not lead_result.get("passes_configured_gates"):
        raise ValueError("Lead fails the fixed EGFR policy: " + ", ".join(lead_result.get("rejection_reasons", [])))
    save(inputs / "reward.json", reward.recipe.model_dump())
    save(inputs / "criteria.json", dict(minimum_portfolio=3, minimum_lower_pic50=6, maximum_pairwise_similarity=.85, novelty="training partition only"))
    save(base / "inputs.json", {"artifacts": [artifact(p) for p in inputs.iterdir() if p.is_file()]})
    if store.get(cid)["state"] == "DRAFT":
        store.transition(cid, "PLANNING", store.get(cid)["revision"])
    with local_server(base / "inference-plan") as url:
        proposal = propose("planner", dict(objective=store.get(cid)["objective"], target=predictor.target, predictor=predictor.identifier, missing_information=[]), LocalProvider(url), base / "agents/planner")
    save(base / "plan.json", dict(objective=dict(identifier="portal-egfr-v1", description=store.get(cid)["objective"], mode="research", target=predictor.target,
        budget=dict(max_jobs=1, max_candidates=count, max_seconds_per_job=600)), rationale=proposal.rationale,
        strategy=dict(run_type="sampling", model_sha256=digest(prior.read_bytes()), seed=seed)))
    store.transition(cid, "AWAITING_PLAN_APPROVAL", store.get(cid)["revision"])


def advance(store, cid):
    base = store.root / cid
    state = store.get(cid)["state"]
    if state == "FORMULATING":
        predictor = Registry(ROOT).optimization_predictor("EGFR-rf-v1")
        with local_server(base / "inference-score") as url:
            propose("formulator", dict(predictor=predictor.identifier, component="conservative_activity_v1", qualification=True), LocalProvider(url), base / "agents/formulator")
        save(base / "score.json", dict(purpose="research", components=[dict(name="activity", weight=1., direction="maximize", predictor_id=predictor.identifier,
            predictor_sha256=predictor.artifact.sha256, recipe_sha256=digest((base / "inputs/reward.json").read_bytes()))]))
        store.transition(cid, "AWAITING_SCORE_APPROVAL", store.get(cid)["revision"])
    elif state == "CONFIGURING":
        plan = json.loads((base / "plan.json").read_bytes())
        out = base / "outputs"
        out.mkdir(exist_ok=True)
        q = lambda p: json.dumps(str(p))
        config = f'run_type="sampling"\ndevice="cpu"\nseed={plan["strategy"]["seed"]}\njson_out_config={q(out / "executed.json")}\n[parameters]\nmodel_file={q(base / "inputs/mol2mol.prior")}\nsmiles_file={q(base / "inputs/lead.smi")}\noutput_file={q(out / "samples.csv")}\nnum_smiles={plan["objective"]["budget"]["max_candidates"]}\nunique_molecules=false\nrandomize_smiles=false\nsample_strategy="multinomial"\ntemperature=1.0\n'
        validate_config(config.encode(), base, plan["objective"]["budget"])
        (base / "config.toml").write_text(config, encoding="utf-8")
        with local_server(base / "inference-config") as url:
            propose("executor", dict(run_type="sampling", approved=True, config_sha256=digest(config.encode())), LocalProvider(url), base / "agents/executor")
        store.transition(cid, "AWAITING_LAUNCH_APPROVAL", store.get(cid)["revision"])
    elif state == "EVALUATING":
        with (base / "outputs/samples.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        column = next(k for k in rows[0] if k.lower() == "smiles")
        reward = ConservativeReward(base / "inputs", json.loads((base / "inputs/reward.json").read_bytes()))
        result = reward.score([r[column] for r in rows])
        # Same fixed portfolio policy as the Stage 7 script, independent implementation.
        from rdkit import Chem, DataStructs
        from rdkit.Chem import rdFingerprintGenerator
        gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
        known = {Chem.MolToSmiles(Chem.MolFromSmiles(s)) for s in reward.predictor.model["training_smiles"]}
        selected, fps = [], []
        for row in sorted(result["rows"], key=lambda r: -r["reward"]):
            row["novel_to_training"] = row.get("canonical_smiles") not in known if row["valid"] else False
            if not row.get("passes_configured_gates") or not row["novel_to_training"] or row["activity"].get("lower", -100) < 6:
                continue
            fp = gen.GetFingerprint(Chem.MolFromSmiles(row["canonical_smiles"]))
            if fps and max(DataStructs.BulkTanimotoSimilarity(fp, fps)) > .85:
                continue
            selected.append(row); fps.append(fp)
        export_evaluation(result, base / "evaluation")
        save(base / "final-portfolio.json", selected)
        met = len(selected) >= 3
        with local_server(base / "inference-analysis") as url:
            analysis = propose("analyser", dict(qualified=True, execution_succeeded=True, criteria_met=met, remaining_iterations=0, candidate_count=len(selected)), LocalProvider(url), base / "agents/analyser")
        with store.transaction() as db:
            job = dict(db.execute("SELECT * FROM jobs WHERE campaign=? ORDER BY created DESC LIMIT 1", (cid,)).fetchone())
        save(base / "evidence.json", dict(campaign=cid, job_id=job["id"], results=dict(artifacts=[artifact(base / "evaluation/evaluation.json"), artifact(base / "evaluation/candidates.parquet"), artifact(base / "final-portfolio.json")]), evaluator_version="portal-conservative-v1", qualified=met, limitations=["Research-only predictions; no experimental activity, selectivity, safety or synthesis validation", "Novelty is relative to the training partition only"]))
        save(base / "analysis.json", dict(decision="complete" if met else "stop", evidence_sha256=digest((base / "evidence.json").read_bytes()), rationale=analysis.rationale))
        store.transition(cid, "ANALYSING", store.get(cid)["revision"])
        store.transition(cid, "COMPLETED" if met else "FAILED", store.get(cid)["revision"])
        store.render(cid)
        (base / "REPORT.md").write_text(f'# EGFR campaign report\n\nGenerated {len(rows)} rows. Portfolio size: {len(selected)}. Frozen criteria met: {met}.\n\n{analysis.rationale}\n\nThese are model predictions, not experimental results. See evaluation JSON/Parquet for intervals, applicability domain and rejection reasons.\n', encoding="utf-8")
    else:
        raise ValueError("No preparation action is available in this state")
