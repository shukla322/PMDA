"""Deterministic orchestration fixtures, explicitly separate from scientific runs."""
import json
from .schemas import Plan
from .store import digest
from .contracts import PolicyError


class MockPlanner:
    def propose(self, model_hash):
        return Plan.model_validate({"objective":{"identifier":"mock","description":"Mock controller exercise","mode":"infrastructure"},
            "rationale":"Deterministic test fixture, not an LLM or scientific plan",
            "strategy":{"run_type":"sampling","model_sha256":model_hash}})


class MockJob:
    def complete(self, store, job_id):
        job=store.job(job_id)
        campaign=store.snapshot(job["campaign"])
        if campaign["objective"]["mode"]!="infrastructure" or job["status"]!="reserved":
            raise PolicyError("Mocks may only finish reserved infrastructure fixtures")
        path=store.artifact(job["campaign"],"outputs/mock.json")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({"mock":True,"scientific_evidence":False,"message":"No chemistry was executed"}),encoding="utf-8")
        result={"mock":True,"job_id":job_id,"config_sha256":job["config_hash"],"status":"succeeded",
                "artifacts":[{"path":"outputs/mock.json","sha256":digest(path.read_bytes()),"size":path.stat().st_size}]}
        with store.transaction() as db:
            store.event(db,job["campaign"],"mock_job_fixture",{"job_id":job_id})
        store.finish_job(job_id,"succeeded",result)
        return result
