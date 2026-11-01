import unittest
from pmda.science import PredictorContract, TargetContract, qualify_prediction


class PredictorTests(unittest.TestCase):
    def setUp(self):
        self.contract = PredictorContract("fixture-only", "a" * 64, "b" * 64,
            "pIC50", "dimensionless", "scaffold", "fixture-report", "fixture-domain",
            "fixture-ensemble", 0.5, "test-human")

    def test_outside_domain_cannot_pass(self):
        self.assertEqual(qualify_prediction(self.contract, 12, 0.1, False, 7)["status"], "unqualified")

    def test_nan_is_error(self):
        self.assertEqual(qualify_prediction(self.contract, float("nan"), 0.1, True, 7)["status"], "error")

    def test_high_uncertainty_cannot_pass(self):
        self.assertEqual(qualify_prediction(self.contract, 12, 0.6, True, 7)["status"], "unqualified")

    def test_direction_is_explicit(self):
        self.assertEqual(qualify_prediction(self.contract, 8, 0.1, True, 7)["status"], "pass")
        self.assertEqual(qualify_prediction(self.contract, 8, 0.1, True, 7, False)["status"], "fail")

    def test_missing_target_is_rejected(self):
        with self.assertRaises(ValueError):
            TargetContract("", "human", "inhibition", "IC50", "nM")
