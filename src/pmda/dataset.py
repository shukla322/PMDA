"""Conservative EGFR curation with row-level provenance and explicit exclusions."""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold

POLICY = "egfr-explicit-wt-exact-binding-v1"


def standardize(smiles):
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None or not mol.GetNumAtoms():
        raise ValueError("invalid_structure")
    if len(Chem.GetMolFrags(mol)) != 1:
        raise ValueError("mixture_or_salt")
    if any(a.GetAtomicNum() not in {1, 5, 6, 7, 8, 9, 15, 16, 17, 35, 53} for a in mol.GetAtoms()):
        raise ValueError("unsupported_element")
    # Normalize functional groups/tautomers and retain charge. RDKit's default
    # tautomer policy may remove tautomer-dependent stereo; see the model card.
    mol = rdMolStandardize.Cleanup(mol)
    mol = rdMolStandardize.TautomerEnumerator().Canonicalize(mol)
    Chem.SanitizeMol(mol)
    return Chem.MolToSmiles(mol, isomericSmiles=True)


def exclusion(row, assay):
    if row.get("target_chembl_id") != "CHEMBL203" or assay.get("target_chembl_id") != "CHEMBL203":
        return "target_mismatch"
    if assay.get("confidence_score") != 9 or assay.get("relationship_type") != "D":
        return "target_assignment"
    if row.get("assay_type") != "B" or row.get("bao_label") != "single protein format":
        return "non_single_protein_binding_format"
    if row.get("target_organism") != "Homo sapiens":
        return "organism"
    if (row.get("standard_type"), row.get("standard_units"), row.get("standard_relation")) != ("IC50", "nM", "="):
        return "endpoint_or_units"
    if row.get("assay_variant_mutation") or row.get("assay_variant_accession"):
        return "explicit_variant"
    description = (row.get("assay_description") or "").lower()
    if re.search(r"mutant|mutation|\b[a-z]\d{2,4}[a-z]\b|deletion|insertion|cell-based|cellular|lysate", description):
        return "variant_or_cell_description"
    if not re.search(r"wild[ -]?type|\bwt\b", description):
        return "wildtype_not_explicit"
    if row.get("data_validity_comment"):
        return "validity_flag"
    if row.get("potential_duplicate"):
        return "duplicate_flag"
    try:
        value = float(row["standard_value"])
        if not math.isfinite(value) or value <= 0:
            return "invalid_value"
    except (TypeError, ValueError, KeyError):
        return "invalid_value"
    if not row.get("document_chembl_id"):
        return "missing_document"
    return None


def curate(snapshot, output):
    snapshot, output = Path(snapshot), Path(output)
    manifest = json.loads((snapshot / "manifest.json").read_bytes())
    if manifest["status"] != "downloaded_not_curated":
        raise ValueError("Incomplete input snapshot")
    for item in manifest["files"]:
        path = (snapshot / item["file"]).resolve()
        if not path.is_relative_to(snapshot.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Raw snapshot integrity failure")
    output.mkdir(parents=True, exist_ok=False)
    assays = {r["assay_chembl_id"]: r for p in snapshot.glob("assay-*.json") for r in json.loads(p.read_bytes())["assays"]}
    rows = [r for p in sorted(snapshot.glob("activity-*.json")) for r in json.loads(p.read_bytes())["activities"]]
    exclusions, groups, decisions = Counter(), defaultdict(list), []
    for row in rows:
        reason = exclusion(row, assays.get(row["assay_chembl_id"], {}))
        canonical = None
        if not reason:
            try:
                canonical = standardize(row.get("canonical_smiles"))
            except ValueError as exc:
                reason = str(exc)
        decisions.append({"activity_id": row["activity_id"], "reason": reason, "canonical_smiles": canonical})
        if reason:
            exclusions[reason] += 1
        else:
            groups[canonical].append(row)
    curated = []
    for smiles, records in sorted(groups.items()):
        values = [9 - math.log10(float(r["standard_value"])) for r in records]
        # Broad cross-assay disagreement is quarantined rather than averaged away.
        if max(values) - min(values) > 1.0:
            exclusions["replicate_conflict_molecules"] += 1
            for decision in decisions:
                if decision["canonical_smiles"] == smiles:
                    decision["reason"] = "replicate_conflict"
            continue
        mol = Chem.MolFromSmiles(smiles)
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
        curated.append({"smiles": smiles, "pic50": statistics.median(values),
            "scaffold": scaffold or "ACYCLIC", "replicate_range": max(values) - min(values),
            "activity_ids": sorted(r["activity_id"] for r in records),
            "assay_ids": sorted({r["assay_chembl_id"] for r in records}),
            "document_ids": sorted({r["document_chembl_id"] for r in records}),
            "latest_year": max((r.get("document_year") or 0) for r in records)})
    def save(name, obj):
        (output / name).write_text(json.dumps(obj, indent=2, allow_nan=False), encoding="utf-8")
    save("curated.json", curated)
    save("row_decisions.json", decisions)
    report = {"policy": POLICY, "raw_records": len(rows), "curated_molecules": len(curated),
        "scaffolds": len({r["scaffold"] for r in curated}), "exclusions": dict(exclusions),
        "source_manifest_sha256": hashlib.sha256((snapshot / "manifest.json").read_bytes()).hexdigest(),
        "curated_sha256": hashlib.sha256((output / "curated.json").read_bytes()).hexdigest(),
        "limitations": ["Wild-type assignment based on explicit assay descriptions, not manual review of every publication",
            "IC50 depends on assay conditions; target confidence does not eliminate assay heterogeneity",
            "Cross-assay medians are a pragmatic research aggregation, not new experimental measurements",
            "No claim of non-covalent mechanism from activity records alone"]}
    save("curation_report.json", report)
    return report
