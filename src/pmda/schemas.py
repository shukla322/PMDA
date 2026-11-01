"""Versioned wire contracts. Unknown fields and non-finite values fail closed."""
from typing import Literal, Annotated
from pathlib import Path
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .contracts import State

Text = Annotated[str, Field(min_length=1)]
SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    schema_version: Literal["1.0"] = "1.0"


class Budget(Contract):
    max_jobs: int = Field(default=3, ge=1, le=100)
    max_seconds_per_job: int = Field(default=600, ge=1, le=3600)
    max_candidates: int = Field(default=100, ge=1, le=10000)


class Target(Contract):
    identifier: Text
    species: Text
    construct_description: Text
    mechanism: Text
    endpoint: Literal["pIC50"]
    limitations: list[Text] = Field(min_length=1)


class Assay(Contract):
    identifier: Text
    target: Text
    confidence: Literal[9]
    endpoint: Literal["IC50"]
    units: Literal["nM"]
    relation: Literal["="]
    construct_evidence: Text
    source_document: Text


class Objective(Contract):
    identifier: Text
    description: Text
    target: Text | None = None
    mode: Literal["infrastructure", "research"]
    budget: Budget = Field(default_factory=Budget)
    @model_validator(mode="after")
    def target_required(self):
        if self.mode == "research" and not self.target:
            raise ValueError("Research objective requires a registered target")
        return self


class GenerationStrategy(Contract):
    run_type: Literal["sampling", "transfer_learning", "staged_learning"]
    device: Literal["cpu"] = "cpu"
    model_sha256: SHA256
    seed: int | None = Field(default=42, ge=0)


class Plan(Contract):
    objective: Objective
    rationale: Text
    strategy: GenerationStrategy


class ScoreComponent(Contract):
    name: Literal["QED", "MolecularWeight", "activity"]
    weight: float = Field(gt=0, le=100)
    direction: Literal["maximize", "minimize", "range"]
    predictor_id: Text | None = None
    predictor_sha256: SHA256 | None = None
    recipe_sha256: SHA256 | None = None
    @model_validator(mode="after")
    def predictor_required(self):
        if self.name == "activity" and (not self.predictor_id or not self.predictor_sha256):
            raise ValueError("Activity score requires a qualified predictor ID and model hash")
        return self


class Score(Contract):
    components: list[ScoreComponent] = Field(min_length=1)
    purpose: Literal["infrastructure", "research"]


class Artifact(Contract):
    path: Text
    sha256: SHA256
    size: int = Field(ge=0)


class ArtifactManifest(Contract):
    artifacts: list[Artifact] = Field(min_length=1)


class Dataset(Contract):
    identifier: Text
    target: Text
    artifact: Artifact
    source_manifest_sha256: SHA256
    curation_version: Text
    endpoint: Literal["pIC50"]
    split_policy: Text
    license_note: Text


class Predictor(Contract):
    identifier: Text
    target: Text
    dataset_sha256: SHA256
    artifact: Artifact
    report: Artifact
    endpoint: Literal["pIC50"]
    intended_use: Text
    domain_method: Text
    uncertainty_method: Text
    eligible_for_optimization: bool
    limitations: list[Text] = Field(min_length=1)


class Campaign(Contract):
    id: Text
    description: Text
    objective: Objective | None = None
    state: State
    revision: int = Field(ge=0)
    iteration: int = Field(ge=0)
    owner: Text | None = None
    budget: Budget
    archived: bool


class Approval(Contract):
    id: Text
    campaign: Text
    kind: Literal["plan", "score", "launch", "revision"]
    artifact_sha256: SHA256
    actor: Text
    acting_role: Literal["scientist", "operator"]
    requested_at: Text
    decided_at: Text
    decision: Literal["approved"] = "approved"
    comments: str = ""
    revision: int = Field(ge=0)


class Execution(Contract):
    id: Text
    campaign: Text
    config_sha256: SHA256
    status: Literal["reserved", "starting", "running", "succeeded", "failed", "cancelled", "timed_out", "ambiguous"]
    pid: int | None = Field(default=None, gt=0)
    error_code: Text | None = None


class Candidate(Contract):
    identifier: Text
    input_smiles: str
    canonical_smiles: str | None
    valid: bool
    evidence_level: int = Field(ge=0, le=3)
    rejection_reasons: list[str]
    activity_status: Literal["unavailable", "qualified", "unqualified", "error"]
    predicted_pic50: float | None = None


class Evidence(Contract):
    campaign: Text
    job_id: Text
    results: ArtifactManifest
    evaluator_version: Text
    qualified: bool
    limitations: list[Text] = Field(min_length=1)


class AnalysisDecision(Contract):
    decision: Literal["complete", "revise", "stop"]
    evidence_sha256: SHA256
    rationale: Text


class Revision(Contract):
    reason: Text
    changes: list[Text] = Field(min_length=1)


CONTRACTS = {c.__name__: c for c in (Budget, Target, Assay, Objective, GenerationStrategy, Plan,
    ScoreComponent, Score, Artifact, ArtifactManifest, Dataset, Predictor, Campaign, Approval,
    Execution, Candidate, Evidence, AnalysisDecision, Revision)}


def export_schemas(destination):
    path = Path(destination)
    path.mkdir(parents=True, exist_ok=True)
    for name, contract in CONTRACTS.items():
        (path / f"{name}.schema.json").write_text(json.dumps(contract.model_json_schema(), indent=2), encoding="utf-8")
