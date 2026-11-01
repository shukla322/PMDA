"""Validated metadata and prediction gates; model fitting is a separate concern."""

from dataclasses import asdict, dataclass
import math
import re


@dataclass(frozen=True)
class TargetContract:
    identifier: str
    species: str
    mechanism: str
    assay_endpoint: str
    units: str

    def __post_init__(self):
        if any(not isinstance(v, str) or not v.strip() for v in asdict(self).values()):
            raise ValueError("Target contract fields must be nonempty strings")


@dataclass(frozen=True)
class PredictorContract:
    identifier: str
    model_sha256: str
    dataset_sha256: str
    endpoint: str
    units: str
    split_strategy: str
    evaluation_report: str
    domain_method: str
    uncertainty_method: str
    maximum_uncertainty: float
    approved_by: str

    def __post_init__(self):
        for key, value in asdict(self).items():
            if key != "maximum_uncertainty" and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"Missing predictor metadata: {key}")
        for value in (self.model_sha256, self.dataset_sha256):
            if re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError("Expected lowercase SHA256 fingerprint")
        if not math.isfinite(self.maximum_uncertainty) or self.maximum_uncertainty < 0:
            raise ValueError("Invalid uncertainty threshold")


def qualify_prediction(contract, value, uncertainty, in_domain, threshold, higher_is_better=True):
    """Unavailable or extrapolated predictions never become positive qualification."""
    if in_domain is not True:
        return {"status": "unqualified", "reason": "outside_or_unknown_domain"}
    if any(v is None or not math.isfinite(v) for v in (value, uncertainty, threshold)):
        return {"status": "error", "reason": "missing_or_nonfinite_prediction"}
    if uncertainty < 0 or uncertainty > contract.maximum_uncertainty:
        return {"status": "unqualified", "reason": "uncertainty_outside_policy"}
    passed = value >= threshold if higher_is_better else value <= threshold
    return {"status": "pass" if passed else "fail", "value": value,
            "uncertainty": uncertainty, "units": contract.units,
            "predictor": contract.identifier, "model_sha256": contract.model_sha256}
