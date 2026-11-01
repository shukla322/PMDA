import json
from pathlib import Path
import tempfile
import unittest
from pmda.evaluation import evaluate,export_evaluation,evaluate_registered
from pmda.registry import Registry
from pmda.predictor import FingerprintPredictor

ROOT=Path(__file__).resolve().parents[1]


class EvidenceTests(unittest.TestCase):
    def test_alerts_are_flags_not_activity_claims(self):
        result=evaluate(["Oc1ccccc1O"])
        self.assertTrue(result["rows"][0]["alerts"])
        self.assertEqual(result["rows"][0]["activity"]["status"],"unavailable")

    def test_evaluation_repeatability(self):
        smiles=["CCO","CC(=O)O","c1ccccc1","CCO"]
        self.assertEqual(evaluate(smiles),evaluate(smiles))

    def test_empty_and_valid_parquet_roundtrip(self):
        import polars as pl
        for smiles in ([],["CCO","invalid"]):
            with tempfile.TemporaryDirectory(dir=ROOT / "runtime/test-tmp") as directory:
                manifest=export_evaluation(evaluate(smiles),directory)
                self.assertIn("candidates.parquet",manifest)
                data=pl.read_parquet(Path(directory) / "candidates.parquet")
                self.assertEqual(data.height,len(smiles))

    def test_registry_integrity_and_immutable_version(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime/test-tmp") as directory:
            registry=Registry(directory)
            record={"identifier":"T","species":"human","construct_description":"WT","mechanism":"inhibition",
                    "endpoint":"pIC50","limitations":["fixture"]}
            registry.register("targets",record)
            with self.assertRaises(FileExistsError):
                registry.register("targets",record)
            with self.assertRaises(ValueError):
                registry.load("targets","../escape")

    def test_registered_model_domain_and_invalid_input(self):
        registry=Registry(ROOT)
        result=evaluate_registered(["CCO","not_smiles"],registry,"EGFR-rf-v1")
        self.assertEqual(result["rows"][0]["activity"]["status"],"unqualified")
        self.assertEqual(result["rows"][1]["activity"]["status"],"unavailable")

    def test_known_heldout_active_inactive_ordering(self):
        registry=Registry(ROOT)
        record=registry.load("predictors","EGFR-rf-v1")
        directory=(ROOT / record.artifact.path).parent
        predictor=FingerprintPredictor(directory)
        rows=json.loads((directory / "splits.json").read_bytes())["test"]
        active=[r for r in rows if r["pic50"]>=7]
        inactive=[r for r in rows if r["pic50"]<=5]
        self.assertGreater(len(active),5)
        # Only five exact low-potency observations survive conservative curation
        # in this held-out split; do not silently relabel higher-potency rows.
        self.assertGreaterEqual(len(inactive),5)
        mean=lambda rows: sum(predictor.predict(r["smiles"])["value"] for r in rows)/len(rows)
        self.assertGreater(mean(active),mean(inactive))
