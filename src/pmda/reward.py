"""Reviewed declarative conservative reward; no generated Python is executed."""
import hashlib
import json
from pathlib import Path
from typing import Literal
from pydantic import Field
from .schemas import Contract, SHA256, Text
from .evaluation import EvaluationPolicy, evaluate
from .dataset import standardize
from .predictor import FingerprintPredictor


class RewardRecipe(Contract):
    component: Literal["conservative_activity_v1"] = "conservative_activity_v1"
    model_sha256: SHA256
    target: Literal["EGFR-human-wt-v1"] = "EGFR-human-wt-v1"
    required_smarts: Text
    mw_max: float = Field(default=500, ge=100, le=600)
    max_logp: float = Field(default=5, ge=0, le=6)
    max_uncertainty: float = Field(default=1.5, gt=0, le=1.5)
    lower_bound_floor: Literal[5.0] = 5.0
    lower_bound_ceiling: Literal[8.0] = 8.0
    reject_alerts: Literal[True] = True


class ConservativeReward:
    def __init__(self, model_directory, recipe):
        self.recipe = RewardRecipe.model_validate(recipe)
        model = Path(model_directory) / "model.json"
        if hashlib.sha256(model.read_bytes()).hexdigest() != self.recipe.model_sha256:
            raise ValueError("Reward model hash mismatch")
        self.predictor = FingerprintPredictor(model_directory)
        if not self.predictor.model["eligible_for_optimization"]:
            raise ValueError("Unqualified reward model")
        self.policy = EvaluationPolicy(mw_max=self.recipe.mw_max, required_smarts=(self.recipe.required_smarts,))

    def score(self, smiles):
        evaluation = evaluate(smiles, policy=self.policy)
        for row in evaluation["rows"]:
            row["reward"] = 0.0
            if not row["valid"]:
                continue
            if row["alerts"]:
                row["rejection_reasons"].append("structural_alert_review_required")
            if row["descriptors"]["logp"] > self.recipe.max_logp:
                row["rejection_reasons"].append("logp_above_policy")
            try:
                prediction = self.predictor.predict(standardize(row["input_smiles"]))
                row["activity"] = prediction
                if prediction["status"] != "qualified":
                    row["rejection_reasons"].append("outside_predictor_domain")
                if prediction["uncertainty_half_width"] > self.recipe.max_uncertainty:
                    row["rejection_reasons"].append("uncertainty_exceeds_policy")
                if not row["rejection_reasons"]:
                    row["reward"] = max(0., min(1., (prediction["lower"] - 5.) / 3.))
                    row["evidence_level"] = 3
            except (ValueError, KeyError, IndexError, ArithmeticError) as exc:
                row["activity"] = {"status": "error", "reason": str(exc)}
                row["rejection_reasons"].append("prediction_failed")
            row["passes_configured_gates"] = not row["rejection_reasons"]
            if row["rejection_reasons"]:
                row["evidence_level"] = 1
        return evaluation


def load_reward(model_file, recipe_file):
    return ConservativeReward(Path(model_file).parent, json.loads(Path(recipe_file).read_bytes()))
