"""Immutable typed metadata registry with verified, BTP-contained artifacts."""
import hashlib
import json
from pathlib import Path
import re
from .schemas import Target, Dataset, Predictor


class Registry:
    TYPES = {"targets": Target, "datasets": Dataset, "predictors": Predictor}

    def __init__(self, project_root):
        self.root = Path(project_root).resolve()

    def verify_artifact(self, artifact):
        path = (self.root / artifact.path).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError("Artifact outside project or missing")
        if path.stat().st_size != artifact.size or hashlib.sha256(path.read_bytes()).hexdigest() != artifact.sha256:
            raise ValueError("Artifact integrity mismatch")

    def _path(self, kind, identifier):
        if kind not in self.TYPES or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identifier):
            raise ValueError("Invalid registry key")
        return self.root / "registries" / kind / (identifier + ".json")

    def register(self, kind, data):
        record = self.TYPES[kind].model_validate(data)
        if kind != "targets":
            self.load("targets", record.target)
            self.verify_artifact(record.artifact)
        if kind == "predictors":
            self.verify_artifact(record.report)
            self.validate_predictor_links(record)
        path = self._path(kind, record.identifier)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents silent replacement of registered scientific versions.
        with path.open("x", encoding="utf-8") as stream:
            stream.write(record.model_dump_json(indent=2))
        return record

    def load(self, kind, identifier):
        record = self.TYPES[kind].model_validate_json(self._path(kind, identifier).read_bytes())
        if kind != "targets":
            self.verify_artifact(record.artifact)
        if kind == "predictors":
            self.verify_artifact(record.report)
            self.validate_predictor_links(record)
        return record

    def validate_predictor_links(self, record):
        report=json.loads((self.root / record.report.path).read_bytes())
        model=json.loads((self.root / record.artifact.path).read_bytes())
        for data in (report,model):
            if data.get("dataset_sha256")!=record.dataset_sha256 or data.get("eligible_for_optimization")!=record.eligible_for_optimization:
                raise ValueError("Predictor metadata disagrees with model/report provenance or qualification")
        datasets=self.root / "registries/datasets"
        matches=[]
        for path in datasets.glob("*.json"):
            dataset=self.load("datasets",path.stem)
            if dataset.artifact.sha256==record.dataset_sha256 and dataset.target==record.target:
                matches.append(dataset.identifier)
        if not matches:
            raise ValueError("Predictor has no matching registered target dataset")

    def optimization_predictor(self, identifier):
        model = self.load("predictors", identifier)
        if not model.eligible_for_optimization:
            raise ValueError("Predictor failed qualification; optimization prohibited")
        return model
