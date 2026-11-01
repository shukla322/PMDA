"""Describe a verified raw snapshot; this does not approve a training dataset."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = Path(sys.argv[1]).resolve()
    if not folder.is_relative_to(ROOT / "data" / "raw"):
        raise ValueError("Snapshot must be inside BTP/data/raw")
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "downloaded_not_curated":
        raise ValueError("Snapshot download is incomplete")
    for item in manifest["files"]:
        path = (folder / item["file"]).resolve()
        if not path.is_relative_to(folder) or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Snapshot manifest integrity failure")
    activities = [r for p in sorted(folder.glob("activity-*.json")) for r in json.loads(p.read_bytes())["activities"]]
    assays = {r["assay_chembl_id"]: r for p in sorted(folder.glob("assay-*.json")) for r in json.loads(p.read_bytes())["assays"]}
    counts = Counter()
    explicit_wildtype_molecules = set()
    for row in activities:
        assay = assays.get(row["assay_chembl_id"], {})
        description = (row.get("assay_description") or "").lower()
        counts["confidence_" + str(assay.get("confidence_score", "missing"))] += 1
        if row.get("assay_variant_mutation"):
            counts["explicit_variant_field"] += 1
        if row.get("data_validity_comment"):
            counts["data_validity_flag"] += 1
        if row.get("potential_duplicate"):
            counts["potential_duplicate_flag"] += 1
        if not row.get("canonical_smiles"):
            counts["missing_smiles"] += 1
        if re.search(r"mutant|mutation|\b[a-z]\d{2,4}[a-z]\b|deletion|insertion", description):
            counts["mutation_description_flag"] += 1
        elif re.search(r"wild[ -]?type|\bwt\b", description):
            counts["wildtype_description_without_mutation_pattern"] += 1
            explicit_wildtype_molecules.add(row["molecule_chembl_id"])
        else:
            counts["construct_unspecified_by_description_heuristic"] += 1
    report = {"status": "feasibility_profile_not_curated", "snapshot": str(folder.relative_to(ROOT)),
              "manifest_sha256": hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest(),
              "release": manifest["release"], "raw_activities": len(activities), "assays_downloaded": len(assays),
              "distinct_molecule_ids": len({r["molecule_chembl_id"] for r in activities}),
              "distinct_assays_in_activities": len({r["assay_chembl_id"] for r in activities}),
              "distinct_documents": len({r["document_chembl_id"] for r in activities if r.get("document_chembl_id")}),
              "distinct_molecule_ids_with_wildtype_description": len(explicit_wildtype_molecules),
              "overlapping_flags_and_confidence_counts": dict(sorted(counts.items())),
              "limitation": "Text heuristics flag review needs; they do not establish construct identity or biological compatibility."}
    output = ROOT / "runtime" / "egfr-feasibility.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
