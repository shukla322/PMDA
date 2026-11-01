"""Deterministic descriptors; never fabricates target activity or safety claims."""

from dataclasses import asdict, dataclass, field
from itertools import combinations
import math


@dataclass(frozen=True)
class EvaluationPolicy:
    mw_min: float = 0
    mw_max: float = 500
    required_smarts: tuple[str, ...] = ()
    forbidden_smarts: tuple[str, ...] = ()

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.mw_min, self.mw_max)) or not 0 <= self.mw_min <= self.mw_max:
            raise ValueError("Invalid molecular-weight interval")


def evaluate(smiles, references=None, policy=None):
    import rdkit
    from rdkit import Chem, DataStructs
    from rdkit.Chem import Descriptors, QED, rdFingerprintGenerator
    from rdkit.Chem.Scaffolds import MurckoScaffold
    from rdkit.Contrib.SA_Score import sascorer
    from rdkit.Chem import FilterCatalog

    policy = policy or EvaluationPolicy()
    catalog_params = FilterCatalog.FilterCatalogParams()
    catalog_params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
    catalog_params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK)
    alerts_catalog = FilterCatalog.FilterCatalog(catalog_params)
    required = [Chem.MolFromSmarts(s) for s in policy.required_smarts]
    forbidden = [Chem.MolFromSmarts(s) for s in policy.forbidden_smarts]
    if any(p is None for p in required + forbidden):
        raise ValueError("Invalid SMARTS policy; no candidates evaluated")
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    ref_mols = [Chem.MolFromSmiles(s) for s in (references or [])]
    if any(m is None for m in ref_mols):
        raise ValueError("Reference set contains invalid molecules")
    ref_canonical = {Chem.MolToSmiles(m, isomericSmiles=True) for m in ref_mols}
    ref_fps = [generator.GetFingerprint(m) for m in ref_mols]
    rows, unique, fps, scaffolds = [], set(), [], set()
    for index, raw in enumerate(smiles):
        row = {"row": index, "input_smiles": raw, "valid": False,
               "evidence_level": 0, "activity": {"status": "unavailable", "reason": "No validated predictor registered"}}
        mol = Chem.MolFromSmiles(raw) if isinstance(raw, str) and raw.strip() else None
        if mol is None or mol.GetNumAtoms() == 0:
            row["rejection_reasons"] = ["invalid_or_empty_smiles"]
            rows.append(row)
            continue
        canonical = Chem.MolToSmiles(mol, isomericSmiles=True)
        fingerprint = generator.GetFingerprint(mol)
        mw = Descriptors.MolWt(mol)
        reasons = []
        if not policy.mw_min <= mw <= policy.mw_max:
            reasons.append("molecular_weight_outside_policy")
        if any(not mol.HasSubstructMatch(p) for p in required):
            reasons.append("required_substructure_missing")
        if any(mol.HasSubstructMatch(p) for p in forbidden):
            reasons.append("forbidden_substructure_present")
        if len(Chem.GetMolFrags(mol)) > 1:
            reasons.append("multifragment_requires_curation")
        duplicate = canonical in unique
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=True)
        if not duplicate:
            unique.add(canonical)
            fps.append(fingerprint)
            scaffolds.add(scaffold)
        row.update(valid=True, canonical_smiles=canonical, duplicate=duplicate,
                   scaffold=scaffold, evidence_level=1 if reasons else 2,
                   rejection_reasons=reasons, passes_configured_gates=not reasons,
                   descriptors={"mw": mw, "logp": Descriptors.MolLogP(mol),
                                "tpsa": Descriptors.TPSA(mol), "hbd": Descriptors.NumHDonors(mol),
                                "hba": Descriptors.NumHAcceptors(mol), "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
                                "formal_charge": Chem.GetFormalCharge(mol), "qed": QED.qed(mol),
                                "sa_heuristic": sascorer.calculateScore(mol)},
                   novelty=None if not ref_fps else canonical not in ref_canonical,
                   nearest_reference_similarity=None if not ref_fps else max(DataStructs.BulkTanimotoSimilarity(fingerprint, ref_fps)))
        row["alerts"] = sorted(match.GetDescription() for match in alerts_catalog.GetMatches(mol))
        row["alert_policy"] = "PAINS and Brenk review flags, not proof of toxicity or automatic rejection"
        d = row["descriptors"]
        row["lipinski_violations"] = sum((d["mw"]>500,d["logp"]>5,d["hbd"]>5,d["hba"]>10))
        if ref_fps:
            similarities = DataStructs.BulkTanimotoSimilarity(fingerprint, ref_fps)
            row["nearest_reference_index"] = max(range(len(similarities)),key=similarities.__getitem__)
        rows.append(row)
    valid = sum(r["valid"] for r in rows)
    # Bound quadratic analysis; retain deterministic first-1000 selection and label it.
    selected = fps[:1000]
    distances = [1 - DataStructs.TanimotoSimilarity(a, b) for a, b in combinations(selected, 2)]
    from rdkit.ML.Cluster import Butina
    lower_triangle = [1-DataStructs.TanimotoSimilarity(selected[i],selected[j]) for i in range(1,len(selected)) for j in range(i)]
    clusters = Butina.ClusterData(lower_triangle,len(selected),.4,isDistData=True,reordering=True) if selected else ()
    return {"schema_version": "1.0", "rdkit_version": rdkit.__version__, "policy": asdict(policy),
            "standardization": "RDKit sanitization and isomeric canonical SMILES; no salt stripping or tautomer normalization",
            "summary": {"total": len(rows), "valid": valid, "unique_valid": len(unique),
                        "validity": valid / len(rows) if rows else None,
                        "uniqueness_among_valid": len(unique) / valid if valid else None,
                        "scaffolds_including_acyclic": len(scaffolds),
                        "internal_diversity": sum(distances) / len(distances) if distances else None,
                        "diversity_sample": "first 1000 unique valid molecules", "pairs": len(distances),
                        "butina_clusters_first_1000": len(clusters), "butina_distance_cutoff": .4},
            "rows": rows}


def evaluate_registered(smiles, registry, predictor_id, references=None, policy=None):
    """A model failure stays explicit; no missing inference is converted to zero."""
    from .dataset import standardize
    from .predictor import FingerprintPredictor
    record = registry.load("predictors",predictor_id)
    predictor = FingerprintPredictor((registry.root / record.artifact.path).parent)
    result = evaluate(smiles,references,policy)
    result["predictor"] = record.model_dump()
    for row in result["rows"]:
        if not row["valid"]:
            continue
        try:
            normalized = standardize(row["input_smiles"])
            prediction = predictor.predict(normalized)
            if not record.eligible_for_optimization:
                prediction["status"] = "unqualified"
            prediction.update(model_sha256=record.artifact.sha256,predictor_id=predictor_id,standardized_input=normalized)
            row["activity"] = prediction
            if prediction["status"]=="qualified" and row["passes_configured_gates"]:
                row["evidence_level"] = 3
        except (ValueError,KeyError,IndexError,TypeError,ArithmeticError) as exc:
            row["activity"] = {"status":"error","reason":str(exc)}
    return result


def export_evaluation(result, directory):
    import hashlib
    import json
    from pathlib import Path
    import polars as pl
    from .schemas import Candidate
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    full = directory / "evaluation.json"
    full.write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    records = []
    for row in result["rows"]:
        data = Candidate(identifier=str(row["row"]),input_smiles=str(row["input_smiles"]) if row["input_smiles"] is not None else "",
            canonical_smiles=row.get("canonical_smiles"),valid=row["valid"],evidence_level=row["evidence_level"],
            rejection_reasons=row.get("rejection_reasons",[]),activity_status=row["activity"]["status"],
            predicted_pic50=row["activity"].get("value")).model_dump()
        data["descriptors_json"] = json.dumps(row.get("descriptors",{}),sort_keys=True)
        data["alerts_json"] = json.dumps(row.get("alerts",[]))
        records.append(data)
    columns = {"schema_version":pl.String,"identifier":pl.String,"input_smiles":pl.String,"canonical_smiles":pl.String,
        "valid":pl.Boolean,"evidence_level":pl.Int64,"rejection_reasons":pl.List(pl.String),"activity_status":pl.String,
        "predicted_pic50":pl.Float64,"descriptors_json":pl.String,"alerts_json":pl.String}
    table = pl.DataFrame(records,schema=columns)
    table.write_parquet(directory / "candidates.parquet")
    manifest = {p.name:{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in (full,directory / "candidates.parquet")}
    (directory / "manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest
