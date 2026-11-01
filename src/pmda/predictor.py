"""CPU fingerprint baseline with frozen scaffold splits and split-conformal intervals.

Artifacts use JSON and NPZ rather than untrusted pickle deserialization.
"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats import spearmanr

GATES = {"min_train": 100, "min_calibration": 30, "min_test": 30,
         "max_mae": 1.0, "min_r2": 0.0, "min_coverage": 0.80,
         "min_domain_fraction": 0.50, "max_interval_width": 3.0}


def fingerprint(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("Invalid prediction structure")
    return rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048).GetFingerprintAsNumPy(mol)


def similarity(a, b):
    intersection = a.astype(np.float32) @ b.astype(np.float32).T
    union = a.sum(axis=1)[:, None] + b.sum(axis=1)[None, :] - intersection
    return intersection / np.maximum(union, 1)


def split(rows):
    # Group allocation is fixed before modeling and independent of endpoint values.
    names = sorted({r["scaffold"] for r in rows}, key=lambda s: hashlib.sha256(("42:" + s).encode()).hexdigest())
    mapping = {s: ("train" if i < int(.65*len(names)) else "calibration" if i < int(.8*len(names)) else "test") for i,s in enumerate(names)}
    return {name: np.array([i for i,r in enumerate(rows) if mapping[r["scaffold"]] == name], dtype=int)
            for name in ("train", "calibration", "test")}


def metrics(y, predicted):
    rho = float(spearmanr(y, predicted).statistic) if np.std(predicted) else None
    return {"mae": float(mean_absolute_error(y, predicted)), "rmse": float(math.sqrt(mean_squared_error(y,predicted))),
            "r2": float(r2_score(y,predicted)), "spearman": rho if rho is None or math.isfinite(rho) else None}


def fit(dataset, destination):
    dataset, destination = Path(dataset), Path(destination)
    rows = json.loads(dataset.read_bytes())
    parts = split(rows)
    for name in parts:
        if len(parts[name]) < GATES["min_" + name]:
            raise ValueError(f"Insufficient {name} observations: {len(parts[name])}")
    destination.mkdir(parents=True, exist_ok=False)
    x = np.stack([fingerprint(r["smiles"]) for r in rows])
    y = np.array([r["pic50"] for r in rows])
    train, cal, test = (parts[n] for n in ("train", "calibration", "test"))
    model = RandomForestRegressor(n_estimators=200, min_samples_leaf=2, max_features=.5, random_state=42, n_jobs=4)
    model.fit(x[train], y[train])
    cal_error = np.abs(y[cal] - model.predict(x[cal]))
    quantile = min(1, math.ceil((len(cal)+1)*.9)/len(cal))
    radius = float(np.quantile(cal_error, quantile, method="higher"))
    train_similarity = similarity(x[train], x[train])
    np.fill_diagonal(train_similarity, -1)
    domain_threshold = max(.35, float(np.quantile(train_similarity.max(axis=1), .05)))
    nearest = similarity(x[test], x[train])
    prediction = model.predict(x[test])
    performance = metrics(y[test], prediction)
    constant = metrics(y[test], np.full(len(test), y[train].mean()))
    neighbor = metrics(y[test], y[train][nearest.argmax(axis=1)])
    domain = nearest.max(axis=1) >= domain_threshold
    coverage = float(np.mean(np.abs(y[test] - prediction) <= radius))
    eligible = bool(performance["mae"] < GATES["max_mae"] and performance["mae"] < constant["mae"]
        and performance["r2"] > GATES["min_r2"] and coverage >= GATES["min_coverage"]
        and domain.mean() >= GATES["min_domain_fraction"] and 2*radius <= GATES["max_interval_width"])
    # Export tree arrays and implement inference without loading executable model objects.
    trees = []
    for estimator in model.estimators_:
        t = estimator.tree_
        trees.append({"left": t.children_left.tolist(), "right": t.children_right.tolist(),
                      "feature": t.feature.tolist(), "threshold": t.threshold.tolist(), "value": t.value[:,0,0].tolist()})
    payload = {"schema_version": "1.0", "trees": trees, "radius": radius,
        "domain_threshold": domain_threshold, "eligible_for_optimization": eligible,
        "training_smiles": [rows[i]["smiles"] for i in train], "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest()}
    (destination / "model.json").write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    np.savez_compressed(destination / "training_fingerprints.npz", x=x[train])
    split_records = {name: [rows[i] for i in indices] for name,indices in parts.items()}
    (destination / "splits.json").write_text(json.dumps(split_records, indent=2), encoding="utf-8")
    train_docs = {d for i in train for d in rows[i]["document_ids"]}
    test_docs = {d for i in test for d in rows[i]["document_ids"]}
    report = {"schema_version": "1.0", "dataset_sha256": payload["dataset_sha256"],
        "split": "fixed hash-ranked scaffold groups, 65/15/20 percent of scaffold groups; row proportions may differ",
        "counts": {name: len(indices) for name,indices in parts.items()}, "seed": 42,
        "test": performance, "mean_baseline": constant, "nearest_neighbor": neighbor,
        "interval_nominal_coverage": .9, "interval_observed_coverage": coverage, "interval_half_width": radius,
        "domain_threshold": domain_threshold, "test_domain_fraction": float(domain.mean()),
        "test_in_domain": metrics(y[test][domain], prediction[domain]) if domain.sum() >= 2 else None,
        "shared_train_test_documents": len(train_docs & test_docs), "gates_predeclared": GATES,
        "eligible_for_optimization": eligible,
        "limitations": ["Research-only cross-assay EGFR pIC50 prediction; not clinical efficacy or safety",
            "Scaffold split does not guarantee publication or temporal independence",
            "Conformal coverage is empirical under scaffold shift; exchangeability is not guaranteed",
            "Similarity threshold is a heuristic applicability domain",
            "Single seed and no external prospective validation; not a completed research benchmark"]}
    (destination / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    exported = FingerprintPredictor(destination)
    reproduced = np.array([exported.predict(rows[i]["smiles"])["value"] for i in test])
    if not np.allclose(reproduced, prediction, atol=1e-10):
        raise RuntimeError("Exported model does not reproduce reference inference")
    return report


class FingerprintPredictor:
    def __init__(self, directory):
        directory = Path(directory)
        self.model = json.loads((directory / "model.json").read_bytes())
        # Reconstruct training fingerprints from the same JSON asset: one inference dependency.
        self.training = np.stack([fingerprint(s) for s in self.model["training_smiles"]])

    def predict(self, smiles):
        x = fingerprint(smiles)
        values = []
        for tree in self.model["trees"]:
            node = 0
            while tree["left"][node] != -1:
                node = tree["left"][node] if x[tree["feature"][node]] <= tree["threshold"][node] else tree["right"][node]
            values.append(tree["value"][node])
        value = float(np.mean(values))
        nearest = float(similarity(x[None, :], self.training).max())
        in_domain = nearest >= self.model["domain_threshold"]
        radius = self.model["radius"]
        return {"value": value, "units": "pIC50", "lower": value-radius, "upper": value+radius,
                "uncertainty_half_width": radius, "nearest_training_similarity": nearest, "in_domain": in_domain,
                "status": "qualified" if in_domain and self.model["eligible_for_optimization"] else "unqualified"}
