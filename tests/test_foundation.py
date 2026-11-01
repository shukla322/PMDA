import tempfile
import unittest
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from pmda.contracts import PolicyError, State
from pmda.store import Store, digest


class CampaignTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / "runtime" / "test-tmp"
        test_root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=test_root)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name, principal="test-human")
        self.cid = self.store.create("Descriptor-only infrastructure campaign")

    def move(self, state):
        self.store.transition(self.cid, state, self.store.get(self.cid)["revision"])

    def approval(self, filename):
        path = self.store.artifact(self.cid, filename)
        base = self.store.root / self.cid
        if filename == "plan.json":
            data = {"objective":{"identifier":"test","description":"Test infrastructure","mode":"infrastructure"},
                    "rationale":"Fixture", "strategy":{"run_type":"sampling","model_sha256":digest(b"fixture-not-an-executable-model")}}
            path.write_text(json.dumps(data), encoding="utf-8")
        elif filename == "score.json":
            path.write_text(json.dumps({"purpose":"infrastructure","components":[{"name":"QED","weight":1,"direction":"maximize"}]}),encoding="utf-8")
        else:
            model = base / "model.prior"
            model.write_bytes(b"fixture-not-an-executable-model")
            (base / "inputs.json").write_text(json.dumps({"artifacts":[{"path":str(model),"sha256":digest(model.read_bytes()),"size":model.stat().st_size}]}),encoding="utf-8")
            path.write_text('run_type="sampling"\ndevice="cpu"\nseed=42\n[parameters]\nnum_smiles=10\nmodel_file='+json.dumps(str(model))+'\noutput_file='+json.dumps(str(base / "outputs/samples.csv")),encoding="utf-8")
        return self.store.approve(self.cid, filename, digest(path.read_bytes()), "test-human")

    def queued(self):
        self.move(State.PLANNING)
        self.move(State.AWAITING_PLAN_APPROVAL)
        self.approval("plan.json")
        self.move(State.AWAITING_SCORE_APPROVAL)
        self.approval("score.json")
        self.move(State.AWAITING_LAUNCH_APPROVAL)
        return self.approval("config.toml")

    def test_cannot_skip_approval(self):
        with self.assertRaises(PolicyError):
            self.move(State.RUNNING)
        self.assertEqual(self.store.get(self.cid)["state"], State.DRAFT)

    def test_stale_revision(self):
        self.move(State.PLANNING)
        with self.assertRaises(PolicyError):
            self.store.transition(self.cid, State.AWAITING_PLAN_APPROVAL, 0)

    def test_path_escape(self):
        with self.assertRaises(PolicyError):
            self.store.artifact(self.cid, "../outside")

    def test_changed_config_blocks_launch(self):
        aid = self.queued()
        self.store.artifact(self.cid, "config.toml").write_bytes(b"changed")
        with self.assertRaises(PolicyError):
            self.store.reserve_launch(self.cid, aid)
        self.assertEqual(self.store.get(self.cid)["state"], State.QUEUED)

    def test_concurrent_launch_only_once(self):
        aid = self.queued()
        def launch():
            try:
                return self.store.reserve_launch(self.cid, aid)[0]
            except PolicyError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: launch(), range(2)))
        self.assertEqual(sum(r is not None for r in results), 1)

    def test_changed_plan_blocks_launch(self):
        aid = self.queued()
        self.store.artifact(self.cid, "plan.json").write_bytes(b"different objective")
        with self.assertRaises(PolicyError):
            self.store.reserve_launch(self.cid, aid)

    def test_wrong_review_hash_cannot_approve(self):
        self.move(State.PLANNING)
        self.move(State.AWAITING_PLAN_APPROVAL)
        self.store.artifact(self.cid, "plan.json").write_bytes(b"current")
        with self.assertRaises(PolicyError):
            self.store.approve(self.cid, "plan.json", digest(b"old"), "test-human")

    def test_restart_preserves_state_and_ledger(self):
        self.queued()
        reopened = Store(self.tmp.name)
        self.assertEqual(reopened.get(self.cid)["state"], State.QUEUED)
        path = reopened.render(self.cid)
        first = path.read_bytes()
        path.unlink()
        self.assertEqual(reopened.render(self.cid).read_bytes(), first)

    def test_terminal_is_immutable(self):
        self.move(State.CANCELLED)
        with self.assertRaises(PolicyError):
            self.move(State.PLANNING)

    def test_changed_input_manifest_blocks_launch(self):
        aid = self.queued()
        self.store.artifact(self.cid,"inputs.json").write_text('{}')
        with self.assertRaises(PolicyError):
            self.store.reserve_launch(self.cid,aid)

    def test_changed_model_blocks_launch(self):
        aid = self.queued()
        self.store.artifact(self.cid,"model.prior").write_bytes(b"altered model")
        with self.assertRaises(PolicyError):
            self.store.reserve_launch(self.cid,aid)

    def test_actor_cannot_impersonate_owner(self):
        self.move(State.PLANNING)
        self.move(State.AWAITING_PLAN_APPROVAL)
        with self.assertRaises(PolicyError):
            self.store.approve(self.cid,"plan.json","a"*64,"someone-else")

    def test_approval_records_acting_role_and_rejects_wrong_role(self):
        aid=self.queued()
        with self.store.transaction() as db:
            approval=dict(db.execute("SELECT * FROM approvals WHERE id=?",(aid,)).fetchone())
        self.assertEqual(approval["acting_role"],"operator")
        self.assertIsNotNone(approval["requested_at"])
        self.store.request_revision(self.cid,"fixture")
        path=self.store.artifact(self.cid,"revision.json")
        path.write_text(json.dumps({"reason":"fixture","changes":["change"]}))
        with self.assertRaises(PolicyError):
            self.store.approve(self.cid,"revision.json",digest(path.read_bytes()),"test-human",acting_role="operator")

    def test_other_principal_cannot_launch_or_transition(self):
        aid = self.queued()
        observer = Store(self.tmp.name,principal="observer")
        with self.assertRaises(PolicyError):
            observer.reserve_launch(self.cid,aid)
        with self.assertRaises(PolicyError):
            observer.transition(self.cid,State.CANCELLED,observer.get(self.cid)["revision"])

    def test_revision_requires_fresh_approvals(self):
        aid = self.queued()
        self.store.request_revision(self.cid,"Change design objective")
        path = self.store.artifact(self.cid,"revision.json")
        path.write_text(json.dumps({"reason":"New objective","changes":["Replan"]}))
        self.store.approve(self.cid,"revision.json",digest(path.read_bytes()),"test-human")
        self.assertEqual(self.store.get(self.cid)["iteration"],1)
        with self.assertRaises(PolicyError):
            self.store.reserve_launch(self.cid,aid)

    def test_append_only_history(self):
        import sqlite3
        before = self.store.verify_history(self.cid)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.transaction() as db:
                db.execute("DELETE FROM events WHERE campaign=?",(self.cid,))
        self.assertEqual(self.store.verify_history(self.cid),before)

    def test_newer_database_rejected(self):
        with self.store.transaction() as db:
            db.execute("PRAGMA user_version=99")
        with self.assertRaises(PolicyError):
            Store(self.tmp.name)

    def test_running_requires_reconciliation(self):
        aid = self.queued()
        self.store.reserve_launch(self.cid,aid)
        with self.assertRaises(PolicyError):
            self.move(State.EVALUATING)
        with self.assertRaises(PolicyError):
            self.move(State.CANCELLED)

    def test_missing_model_never_launches(self):
        aid = self.queued()
        self.store.artifact(self.cid,"model.prior").unlink()
        with self.assertRaises(PolicyError):
            self.store.reserve_launch(self.cid,aid)

    def test_terminal_job_reconciliation_is_idempotent(self):
        aid = self.queued()
        jid,_ = self.store.reserve_launch(self.cid,aid)
        self.store.finish_job(jid,"succeeded",{"fixture":True})
        revision = self.store.get(self.cid)["revision"]
        self.store.finish_job(jid,"succeeded",{"fixture":True})
        self.assertEqual(self.store.get(self.cid)["revision"],revision)
        with self.assertRaises(PolicyError):
            self.store.finish_job(jid,"failed",{})

    def test_missing_evidence_prevents_completion(self):
        aid = self.queued()
        jid,_ = self.store.reserve_launch(self.cid,aid)
        self.store.finish_job(jid,"succeeded",{})
        self.move(State.ANALYSING)
        with self.assertRaises(FileNotFoundError):
            self.move(State.COMPLETED)

    def test_ambiguous_job_is_not_relaunched(self):
        from pmda.execution import ExecutionService
        aid = self.queued()
        jid,_ = self.store.reserve_launch(self.cid,aid)
        with self.store.transaction() as db:
            db.execute("UPDATE jobs SET created='2000-01-01T00:00:00+00:00' WHERE id=?",(jid,))
        self.assertEqual(ExecutionService(self.store).reconcile(jid)["status"],"ambiguous")
        with self.assertRaises(PolicyError):
            self.store.reserve_launch(self.cid,aid)

    def test_owner_can_abandon_missing_supervisor_without_retry(self):
        from pmda.execution import ExecutionService
        aid=self.queued()
        jid,_=self.store.reserve_launch(self.cid,aid)
        with self.store.transaction() as db:
            db.execute("UPDATE jobs SET created='2000-01-01T00:00:00+00:00' WHERE id=?",(jid,))
        service=ExecutionService(self.store)
        result=service.abandon_orphan(jid)
        self.assertEqual(result["status"],"cancelled")
        self.assertEqual(self.store.get(self.cid)["state"],State.CANCELLED)
        with self.assertRaises(PolicyError):
            self.store.reserve_launch(self.cid,aid)

    def test_archive_preserves_audit(self):
        self.move(State.CANCELLED)
        self.store.archive(self.cid)
        self.assertEqual(self.store.list_campaigns(),[])
        self.assertEqual(len(self.store.list_campaigns(True)),1)
        self.store.verify_history(self.cid)

    def test_transaction_crash_rolls_back_state_and_event(self):
        before=self.store.get(self.cid)
        count=len(self.store.history(self.cid))
        with self.assertRaises(RuntimeError):
            with self.store.transaction() as db:
                self.store.change(db,before,State.PLANNING)
                raise RuntimeError("injected transaction failure")
        self.assertEqual(self.store.get(self.cid),before)
        self.assertEqual(len(self.store.history(self.cid)),count)

    def test_failed_launch_reservation_rolls_back(self):
        from unittest.mock import patch
        aid=self.queued()
        before=self.store.get(self.cid)
        change=self.store.change
        def crash(*args):
            change(*args)
            raise RuntimeError("injected failure before commit")
        with patch.object(self.store,"change",side_effect=crash):
            with self.assertRaises(RuntimeError):
                self.store.reserve_launch(self.cid,aid)
        self.assertEqual(self.store.get(self.cid),before)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],0)
        self.store.reserve_launch(self.cid,aid)

    def test_mock_campaign_completes_with_explicit_non_scientific_evidence(self):
        from pmda.mocks import MockJob
        aid=self.queued()
        jid,_=self.store.reserve_launch(self.cid,aid)
        result=MockJob().complete(self.store,jid)
        path=self.store.artifact(self.cid,"evidence.json")
        path.write_text(json.dumps({"campaign":self.cid,"job_id":jid,"results":{"artifacts":result["artifacts"]},
            "evaluator_version":"mock-v1","qualified":False,"limitations":["No scientific execution"]}))
        self.store.artifact(self.cid,"analysis.json").write_text(json.dumps({"decision":"complete","evidence_sha256":digest(path.read_bytes()),"rationale":"Mock controller check"}))
        self.move(State.ANALYSING)
        self.move(State.COMPLETED)
        self.assertEqual(self.store.snapshot(self.cid)["state"],State.COMPLETED)
        self.store.verify_history(self.cid)

    def test_orphan_process_is_identified_and_stopped(self):
        import subprocess,sys,psutil
        from pmda.execution import ExecutionService
        aid=self.queued()
        jid,config=self.store.reserve_launch(self.cid,aid)
        work=self.store.artifact(self.cid,"jobs/"+jid)
        work.mkdir(parents=True)
        path=work / "approved.toml"
        path.write_bytes(config)
        proc=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)",str(path)],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        try:
            (work / "engine.json").write_text(json.dumps({"pid":proc.pid,"created":psutil.Process(proc.pid).create_time()}))
            with self.store.transaction() as db:
                db.execute("UPDATE jobs SET created='2000-01-01T00:00:00+00:00' WHERE id=?",(jid,))
            result=ExecutionService(self.store).abandon_orphan(jid)
            self.assertEqual(result["status"],"cancelled")
            proc.wait(timeout=10)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)

    def test_all_states_survive_reopen(self):
        for state in State:
            with self.subTest(state=state):
                with self.store.transaction() as db:
                    db.execute("UPDATE campaigns SET state=? WHERE id=?",(state,self.cid))
                reopened=Store(self.tmp.name,principal="test-human")
                self.assertEqual(reopened.get(self.cid)["state"],state)

    def test_illegal_transition_matrix(self):
        from pmda.contracts import TRANSITIONS,TERMINAL
        for source in State:
            for target in State:
                if source not in TERMINAL and target in TRANSITIONS.get(source,set()) | {State.FAILED,State.CANCELLED}:
                    continue
                with self.subTest(source=source,target=target):
                    with self.store.transaction() as db:
                        db.execute("UPDATE campaigns SET state=? WHERE id=?",(source,self.cid))
                    with self.assertRaises(PolicyError):
                        self.store.transition(self.cid,target,self.store.get(self.cid)["revision"])

    def test_old_schema_migrates_without_approval_ownership(self):
        import sqlite3
        legacy=self.store.root / "legacy"
        legacy.mkdir()
        with sqlite3.connect(legacy / "campaigns.sqlite3") as db:
            db.execute("CREATE TABLE campaigns (id TEXT PRIMARY KEY, objective TEXT NOT NULL,state TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 0)")
            db.execute("INSERT INTO campaigns VALUES (?,?,?,0)",(self.cid,"legacy",State.DRAFT))
        db.close()
        migrated=Store(legacy,principal="test-human")
        self.assertEqual(migrated.get(self.cid)["objective"],"legacy")
        self.assertIsNone(migrated.get(self.cid)["owner"])
        with self.assertRaises(PolicyError):
            migrated.transition(self.cid,State.PLANNING,0)


class ChemistryTests(unittest.TestCase):
    def test_validity_duplicates_and_missing_predictor(self):
        from pmda.evaluation import evaluate
        data = evaluate(["CCO", "OCC", "", "not_smiles", "CC(=O)O"], ["CCO"])
        self.assertEqual(data["summary"]["valid"], 3)
        self.assertEqual(data["summary"]["unique_valid"], 2)
        self.assertTrue(data["rows"][1]["duplicate"])
        self.assertFalse(data["rows"][0]["novelty"])
        self.assertEqual(data["rows"][0]["activity"]["status"], "unavailable")
        self.assertAlmostEqual(data["rows"][0]["descriptors"]["mw"], 46.069, places=2)

    def test_constraint_and_invalid_policy(self):
        from pmda.evaluation import EvaluationPolicy, evaluate
        data = evaluate(["CCO"], policy=EvaluationPolicy(required_smarts=("c1ccccc1",)))
        self.assertIn("required_substructure_missing", data["rows"][0]["rejection_reasons"])
        with self.assertRaises(ValueError):
            evaluate(["CCO"], policy=EvaluationPolicy(forbidden_smarts=("[",)))

    def test_empty_is_not_success(self):
        from pmda.evaluation import evaluate
        self.assertIsNone(evaluate([])["summary"]["validity"])


if __name__ == "__main__":
    unittest.main()
