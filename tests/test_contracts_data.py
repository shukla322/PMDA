import json
import unittest
from pydantic import ValidationError
from pmda.schemas import Budget, Objective, ScoreComponent, Target
from pmda.dataset import standardize, exclusion
from pmda.predictor import split


class SchemaTests(unittest.TestCase):
    def test_nonfinite_and_unknown_fields(self):
        with self.assertRaises(ValidationError):
            ScoreComponent(name="QED",weight=float("nan"),direction="maximize")
        with self.assertRaises(ValidationError):
            Budget(max_jobs=1,ignore_approval=True)

    def test_research_requires_target(self):
        with self.assertRaises(ValidationError):
            Objective(identifier="x",description="test",mode="research")

    def test_activity_requires_predictor(self):
        with self.assertRaises(ValidationError):
            ScoreComponent(name="activity",weight=1,direction="maximize")

    def test_budget_bounds(self):
        for value in (0,-1,100000):
            with self.assertRaises(ValidationError):
                Budget(max_jobs=value)


class CurationTests(unittest.TestCase):
    def test_equivalent_molecules_normalize(self):
        self.assertEqual(standardize("CCO"),standardize("OCC"))

    def test_salts_and_invalid_rejected(self):
        for smiles in ("", "not_smiles", "CCO.[Na+]", "[Fe]"):
            with self.assertRaises(ValueError):
                standardize(smiles)

    def test_stereoisomers_distinct(self):
        self.assertNotEqual(standardize("C[C@H](O)F"),standardize("C[C@@H](O)F"))

    def test_charge_retained(self):
        self.assertIn("+",standardize("C[NH3+]"))

    def test_scaffolds_disjoint_and_repeatable(self):
        rows = [{"scaffold":str(i//2)} for i in range(100)]
        first,second=split(rows),split(rows)
        groups = []
        for name in first:
            self.assertEqual(first[name].tolist(),second[name].tolist())
            groups.append({rows[i]["scaffold"] for i in first[name]})
        self.assertFalse(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])

    def test_mutant_and_ambiguous_not_wildtype(self):
        assay={"target_chembl_id":"CHEMBL203","confidence_score":9,"relationship_type":"D"}
        row={"target_chembl_id":"CHEMBL203","assay_type":"B","bao_label":"single protein format",
             "target_organism":"Homo sapiens","standard_type":"IC50","standard_units":"nM","standard_relation":"=",
             "standard_value":"10","document_chembl_id":"D1"}
        self.assertEqual(exclusion(row,assay),"wildtype_not_explicit")
        row["assay_description"]="Wild type EGFR and T790M mutant"
        self.assertEqual(exclusion(row,assay),"variant_or_cell_description")
        row["assay_description"]="Inhibition of wild type EGFR"
        self.assertIsNone(exclusion(row,assay))
        row["standard_relation"]="<"
        self.assertEqual(exclusion(row,assay),"endpoint_or_units")
