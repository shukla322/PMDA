"""Materialize reviewable prompt, component and schema registries."""
import hashlib
import json
from pathlib import Path
from pmda.agents import SCHEMAS, FIELDS, RULES
from pmda.reward import RewardRecipe
from pmda.schemas import export_schemas

ROOT = Path(__file__).resolve().parents[1]
export_schemas(ROOT / "schemas/v1")
for role, schema in SCHEMAS.items():
    path = ROOT / f"schemas/v1/{schema.__name__}.schema.json"
    path.write_text(json.dumps(schema.model_json_schema(), indent=2), encoding="utf-8")
directory = ROOT / "registries/agents"
directory.mkdir(parents=True, exist_ok=True)
for role in SCHEMAS:
    record = dict(role=role, version="1.0", rule=RULES[role], context_fields=FIELDS[role], tools=[],
                  max_attempts=2, max_output_tokens=384, authority="Advisory only; no controller, approvals or subprocess access")
    (directory / f"{role}-v1.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
directory = ROOT / "registries/components"
directory.mkdir(parents=True, exist_ok=True)
source = ROOT / "src/pmda/reward.py"
record = dict(identifier="conservative_activity_v1", source=str(source.relative_to(ROOT)),
              source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              scope="Research-only EGFR reward with uncertainty/domain/property gates",
              executable_generation_allowed=False, schema=RewardRecipe.model_json_schema())
(directory / "conservative_activity_v1.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print("Exported role, component and wire contracts")
