"""Transactional campaign state. No agent or markdown file owns transitions."""

import hashlib
import json
import sqlite3
import uuid
import getpass
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .contracts import APPROVAL_ROUTES, TERMINAL, TRANSITIONS, PolicyError, State


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self, root, principal=None):
        self.principal = principal or getpass.getuser()
        self.root = Path(root).resolve()
        if not self.root.is_relative_to(Path(__file__).resolve().parents[2]):
            raise PolicyError("Campaign storage must stay inside BTP")
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "campaigns.sqlite3"
        with self.transaction() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS campaigns (
                  id TEXT PRIMARY KEY, objective TEXT NOT NULL,
                  state TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS events (
                  seq INTEGER PRIMARY KEY AUTOINCREMENT, campaign TEXT NOT NULL,
                  time TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS approvals (
                  id TEXT PRIMARY KEY, campaign TEXT NOT NULL, kind TEXT NOT NULL,
                  revision INTEGER NOT NULL, path TEXT NOT NULL, hash TEXT NOT NULL,
                  actor TEXT NOT NULL, time TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, campaign TEXT NOT NULL, approval TEXT UNIQUE NOT NULL,
                  status TEXT NOT NULL, pid INTEGER);
            ''')
        self.migrate()

    def migrate(self):
        """Additive v1 -> v2 migration; future versions are rejected, not guessed."""
        with self.transaction() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 5:
                raise PolicyError("Database is newer than this application")
            if version < 2:
                additions = {
                    "campaigns": [("iteration", "INTEGER NOT NULL DEFAULT 0"), ("owner", "TEXT"),
                        ("budget", "TEXT NOT NULL DEFAULT '{\"max_jobs\":3,\"max_seconds_per_job\":600,\"max_candidates\":100}'")],
                    "approvals": [("iteration", "INTEGER NOT NULL DEFAULT 0"), ("content", "BLOB")],
                    "jobs": [("created", "TEXT"), ("config_hash", "TEXT"), ("result", "TEXT")],
                    "events": [("previous_hash", "TEXT"), ("event_hash", "TEXT")]}
                for table, columns in additions.items():
                    present = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
                    for column, definition in columns:
                        if column not in present:
                            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                # Legacy campaigns have no verified owner; they remain read-only for approval.
                previous = {}
                for event in db.execute("SELECT * FROM events ORDER BY seq").fetchall():
                    prev = previous.get(event["campaign"], "0"*64)
                    hashed = self.event_digest(event["campaign"], event["time"], event["kind"], event["payload"], prev)
                    db.execute("UPDATE events SET previous_hash=?,event_hash=? WHERE seq=?", (prev,hashed,event["seq"]))
                    previous[event["campaign"]] = hashed
                db.execute("PRAGMA user_version=2")
            if version < 3:
                db.execute("ALTER TABLE approvals ADD COLUMN inputs_hash TEXT")
                db.execute("PRAGMA user_version=3")
            if version < 4:
                db.execute("ALTER TABLE campaigns ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
                db.execute("ALTER TABLE jobs ADD COLUMN candidates INTEGER NOT NULL DEFAULT 0")
                db.execute("PRAGMA user_version=4")
            if version < 5:
                db.execute("ALTER TABLE approvals ADD COLUMN acting_role TEXT NOT NULL DEFAULT 'legacy_unrecorded'")
                db.execute("ALTER TABLE approvals ADD COLUMN requested_at TEXT")
                db.execute("ALTER TABLE approvals ADD COLUMN decision TEXT NOT NULL DEFAULT 'approved'")
                db.execute("ALTER TABLE approvals ADD COLUMN comments TEXT NOT NULL DEFAULT ''")
                db.execute("PRAGMA user_version=5")
            db.execute("CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append-only events'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append-only events'); END")

    @staticmethod
    def event_digest(cid, time, kind, payload, previous):
        return digest(json.dumps([cid,time,kind,payload,previous], separators=(",", ":")).encode())

    def connect(self):
        db = sqlite3.connect(self.db, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def event(self, db, cid, kind, payload):
        last = db.execute("SELECT event_hash FROM events WHERE campaign=? ORDER BY seq DESC LIMIT 1", (cid,)).fetchone()
        previous = last[0] if last else "0"*64
        timestamp, encoded = now(), json.dumps(payload, sort_keys=True, allow_nan=False)
        hashed = self.event_digest(cid, timestamp, kind, encoded, previous)
        db.execute("INSERT INTO events(campaign,time,kind,payload,previous_hash,event_hash) VALUES (?,?,?,?,?,?)",
                   (cid, timestamp, kind, encoded, previous, hashed))

    def row(self, db, cid):
        row = db.execute("SELECT * FROM campaigns WHERE id=?", (cid,)).fetchone()
        if row is None:
            raise PolicyError("Unknown campaign")
        return dict(row)

    def get(self, cid):
        with self.transaction() as db:
            return self.row(db, cid)

    def snapshot(self, cid):
        from .schemas import Campaign, Plan, Budget
        with self.transaction() as db:
            row=self.row(db,cid)
            plan=db.execute("SELECT content FROM approvals WHERE campaign=? AND iteration=? AND kind='plan' ORDER BY time DESC LIMIT 1",(cid,row["iteration"])).fetchone()
            objective=Plan.model_validate_json(plan[0]).objective if plan and plan[0] else None
            return Campaign(id=cid,description=row["objective"],objective=objective,state=State(row["state"]),
                revision=row["revision"],iteration=row["iteration"],owner=row["owner"],budget=Budget.model_validate_json(row["budget"]),archived=bool(row["archived"])).model_dump(mode="json")

    def create(self, objective):
        if not objective.strip():
            raise PolicyError("Objective must not be empty")
        cid = str(uuid.uuid4())
        with self.transaction() as db:
            db.execute("INSERT INTO campaigns(id,objective,state,owner) VALUES (?,?,?,?)",
                       (cid, objective, State.DRAFT, self.principal))
            self.event(db, cid, "created", {"objective": objective})
        (self.root / cid).mkdir()
        return cid

    def change(self, db, row, target):
        db.execute("UPDATE campaigns SET state=?, revision=revision+1 WHERE id=?",
                   (target, row["id"]))
        self.event(db, row["id"], "transition", {"from": row["state"], "to": target})

    def transition(self, cid, target, expected_revision):
        target = State(target)
        with self.transaction() as db:
            row = self.row(db, cid)
            source = State(row["state"])
            if row["owner"] != self.principal:
                raise PolicyError("Only campaign owner may transition")
            if row["revision"] != expected_revision:
                raise PolicyError("Stale revision; reload campaign")
            if source in TERMINAL:
                raise PolicyError("Terminal campaign cannot transition")
            # Launch reservation, not a generic state update, owns QUEUED -> RUNNING.
            allowed = TRANSITIONS.get(source, set()) - {State.RUNNING}
            if target not in allowed | {State.FAILED, State.CANCELLED}:
                raise PolicyError(f"Illegal transition: {source} -> {target}")
            if source == State.RUNNING:
                raise PolicyError("Running jobs transition only through reconciliation/cancellation")
            if target == State.COMPLETED:
                from .schemas import Evidence, AnalysisDecision
                evidence_path = self.artifact(cid, "evidence.json")
                evidence = Evidence.model_validate_json(evidence_path.read_bytes())
                from .schemas import Plan
                approved_plan = db.execute("SELECT content FROM approvals WHERE campaign=? AND iteration=? AND kind='plan' ORDER BY time DESC LIMIT 1", (cid,row["iteration"])).fetchone()
                if approved_plan and Plan.model_validate_json(approved_plan[0]).objective.mode == "research" and not evidence.qualified:
                    raise PolicyError("Research success requires qualified evidence; unmet objectives must stop explicitly")
                decision = AnalysisDecision.model_validate_json(self.artifact(cid, "analysis.json").read_bytes())
                if evidence.campaign != cid or decision.decision != "complete" or decision.evidence_sha256 != digest(evidence_path.read_bytes()):
                    raise PolicyError("Completion requires matching evidence and analysis")
                job = db.execute("SELECT status FROM jobs WHERE id=? AND campaign=?", (evidence.job_id,cid)).fetchone()
                if not job or job[0] != "succeeded":
                    raise PolicyError("Completion requires a successful registered job")
                for item in evidence.results.artifacts:
                    path = self.artifact(cid, item.path)
                    if path.stat().st_size != item.size or digest(path.read_bytes()) != item.sha256:
                        raise PolicyError("Completion artifact mismatch")
            self.change(db, row, target)

    def artifact(self, cid, relative):
        try:
            uuid.UUID(cid)
        except (ValueError, TypeError, AttributeError) as exc:
            raise PolicyError("Invalid campaign identifier") from exc
        base = (self.root / cid).resolve()
        path = (base / relative).resolve()
        if not path.is_relative_to(base) or path == base:
            raise PolicyError("Artifact must stay inside its campaign")
        return path

    def approve(self, cid, relative, expected_hash, actor, acting_role=None, comments=""):
        if not actor.strip() or actor != self.principal:
            raise PolicyError("Approval actor must match the authenticated local principal")
        path = self.artifact(cid, relative)
        data = path.read_bytes()
        if digest(data) != expected_hash:
            raise PolicyError("Artifact changed since review")
        aid = str(uuid.uuid4())
        with self.transaction() as db:
            row = self.row(db, cid)
            if row["owner"] != self.principal:
                raise PolicyError("Only the campaign owner may approve")
            route = APPROVAL_ROUTES.get(State(row["state"]))
            if route is None:
                raise PolicyError("Campaign is not awaiting an implemented approval type")
            kind, target = route
            required_role="operator" if kind=="launch" else "scientist"
            role=acting_role or required_role
            if role!=required_role:
                raise PolicyError("Approval acting role does not permit this decision")
            from .schemas import Plan, Score, Revision
            if kind in {"plan", "score", "revision"}:
                record = {"plan": Plan, "score": Score, "revision": Revision}[kind].model_validate_json(data)
                if kind == "plan":
                    if record.objective.mode == "research":
                        from .registry import Registry
                        Registry(Path(__file__).resolve().parents[2]).load("targets",record.objective.target)
                    db.execute("UPDATE campaigns SET budget=?,objective=? WHERE id=?", (record.objective.budget.model_dump_json(),record.objective.description, cid))
                if kind == "score":
                    from .registry import Registry
                    registry = Registry(Path(__file__).resolve().parents[2])
                    plan_row=db.execute("SELECT content FROM approvals WHERE campaign=? AND iteration=? AND kind='plan' ORDER BY time DESC LIMIT 1",(cid,row["iteration"])).fetchone()
                    plan=Plan.model_validate_json(plan_row[0])
                    if record.purpose!=plan.objective.mode:
                        raise PolicyError("Score purpose differs from approved objective")
                    for component in record.components:
                        if component.name == "activity":
                            predictor=registry.optimization_predictor(component.predictor_id)
                            if predictor.target!=plan.objective.target:
                                raise PolicyError("Predictor target differs from approved objective")
                            if predictor.artifact.sha256!=component.predictor_sha256:
                                raise PolicyError("Score predictor hash differs from registered model")
            elif kind == "launch":
                import tomllib
                tomllib.loads(data.decode("utf-8"))
                from .execution import validate_config
                parsed = validate_config(data, self.root / cid, json.loads(row["budget"]))
                plan_row = db.execute("SELECT content FROM approvals WHERE campaign=? AND iteration=? AND kind='plan' ORDER BY time DESC LIMIT 1",(cid,row["iteration"])).fetchone()
                plan = Plan.model_validate_json(plan_row[0])
                if plan.strategy.run_type != parsed["run_type"]:
                    raise PolicyError("Config run type differs from approved strategy")
                if plan.strategy.seed is not None and parsed.get("seed") != plan.strategy.seed:
                    raise PolicyError("Config seed differs from approved strategy")
                score_row = db.execute("SELECT content FROM approvals WHERE campaign=? AND iteration=? AND kind='score' ORDER BY time DESC LIMIT 1", (cid,row["iteration"])).fetchone()
                score = Score.model_validate_json(score_row[0])
                for stage in parsed.get("stage", []):
                    expected_components = sorted((c.name, c.weight) for c in score.components)
                    actual_components = sorted(({"QED": "QED", "PMDAActivity": "activity"}[name], endpoint.get("weight", 1.0))
                        for component in stage["scoring"]["component"] for name, definition in component.items() for endpoint in definition["endpoint"])
                    if actual_components != expected_components:
                        raise PolicyError("RL components or weights differ from approved score")
                    for entry in stage["scoring"]["component"]:
                        if "PMDAActivity" in entry:
                            params = entry["PMDAActivity"]["endpoint"][0]["params"]
                            model_hash = digest(Path(params["model_file"]).read_bytes())
                            recipe_bytes = Path(params["recipe_file"]).read_bytes()
                            recipe = json.loads(recipe_bytes)
                            if recipe["target"] != plan.objective.target or not any(c.name == "activity" and c.predictor_sha256 == model_hash and c.recipe_sha256 == digest(recipe_bytes) for c in score.components):
                                raise PolicyError("Reward differs from approved score/model/target")
                model_keys = {"sampling":"model_file","transfer_learning":"input_model_file","staged_learning":"prior_file"}
                model = Path(parsed["parameters"][model_keys[parsed["run_type"]]])
                if digest(model.read_bytes()) != plan.strategy.model_sha256:
                    raise PolicyError("Config model differs from approved strategy")
            if kind == "revision":
                db.execute("UPDATE campaigns SET iteration=iteration+1 WHERE id=?", (cid,))
            db.execute("INSERT INTO approvals(id,campaign,kind,revision,path,hash,actor,time,iteration,content) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (aid, cid, kind, row["revision"], str(path), expected_hash, actor, now(),row["iteration"],data))
            if kind == "launch":
                db.execute("UPDATE approvals SET inputs_hash=? WHERE id=?", (digest(self.artifact(cid,"inputs.json").read_bytes()),aid))
            request=db.execute("SELECT time FROM events WHERE campaign=? AND kind='transition' ORDER BY seq DESC LIMIT 1",(cid,)).fetchone()
            db.execute("UPDATE approvals SET acting_role=?,requested_at=?,comments=? WHERE id=?",(role,request[0] if request else now(),comments,aid))
            self.event(db, cid, "approved", {"id": aid, "kind": kind, "hash": expected_hash, "actor": actor,"acting_role":role,"comments":comments})
            self.change(db, row, target)
        return aid

    def reserve_launch(self, cid, aid):
        """Reserve once before external execution; ambiguous crashes require reconciliation."""
        with self.transaction() as db:
            row = self.row(db, cid)
            approval = db.execute("SELECT * FROM approvals WHERE id=? AND campaign=? AND kind='launch'",
                                  (aid, cid)).fetchone()
            if row["owner"] != self.principal:
                raise PolicyError("Only campaign owner may launch")
            if approval is None or row["state"] != State.QUEUED:
                raise PolicyError("No valid queued launch approval")
            if row["revision"] != approval["revision"] + 1:
                raise PolicyError("Approval does not match current revision")
            if digest(self.artifact(cid,"inputs.json").read_bytes()) != approval["inputs_hash"]:
                raise PolicyError("Approved input manifest changed")
            budget = json.loads(row["budget"])
            if db.execute("SELECT COUNT(*) FROM jobs WHERE campaign=?", (cid,)).fetchone()[0] >= budget["max_jobs"]:
                raise PolicyError("Campaign job budget exhausted")
            for dependency in db.execute("SELECT path,hash FROM approvals WHERE campaign=? AND iteration=?", (cid,row["iteration"])):
                dependency_path = Path(dependency["path"])
                self.artifact(cid, dependency_path)
                if digest(dependency_path.read_bytes()) != dependency["hash"]:
                    raise PolicyError("An approved campaign artifact changed; re-review is required")
            config = Path(approval["path"]).read_bytes()
            if digest(config) != approval["hash"]:
                raise PolicyError("Approved configuration was modified")
            from .execution import validate_config, candidate_count
            proposed = candidate_count(validate_config(config, self.root / cid, budget))
            consumed = db.execute("SELECT COALESCE(SUM(candidates),0) FROM jobs WHERE campaign=?",(cid,)).fetchone()[0]
            if consumed + proposed > budget["max_candidates"]:
                raise PolicyError("Campaign candidate budget exhausted")
            jid = str(uuid.uuid4())
            db.execute("INSERT INTO jobs(id,campaign,approval,status,pid,created,config_hash) VALUES (?,?,?,'reserved',NULL,?,?)", (jid, cid, aid, now(),digest(config)))
            db.execute("UPDATE jobs SET candidates=? WHERE id=?",(proposed,jid))
            self.change(db, row, State.RUNNING)
            self.event(db, cid, "launch_reserved", {"job_id": jid, "approval": aid})
        return jid, config

    def job(self, jid):
        with self.transaction() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            if row is None:
                raise PolicyError("Unknown job")
            return dict(row)

    def finish_job(self, jid, status, result):
        if status not in {"succeeded", "failed", "cancelled", "timed_out", "ambiguous"}:
            raise PolicyError("Invalid final status")
        with self.transaction() as db:
            job = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            if job is None:
                raise PolicyError("Unknown job")
            if job["status"] in {"succeeded", "failed", "cancelled", "timed_out"}:
                if job["status"] != status:
                    raise PolicyError("Conflicting final job status")
                return
            db.execute("UPDATE jobs SET status=?,result=? WHERE id=?", (status,json.dumps(result),jid))
            self.event(db, job["campaign"], "job_"+status, result)
            row = self.row(db, job["campaign"])
            if status != "ambiguous":
                target = State.EVALUATING if status == "succeeded" else State.CANCELLED if status == "cancelled" else State.FAILED
                self.change(db,row,target)

    def request_revision(self, cid, reason):
        """Explicit invalidation route; running/terminal campaigns cannot be rewritten."""
        if not reason.strip():
            raise PolicyError("Revision requires a reason")
        with self.transaction() as db:
            row = self.row(db,cid)
            if row["owner"] != self.principal or State(row["state"]) in TERMINAL | {State.RUNNING}:
                raise PolicyError("Cannot revise this campaign")
            self.change(db,row,State.AWAITING_REVISION_APPROVAL)
            self.event(db,cid,"revision_requested",{"reason":reason})

    def verify_history(self, cid):
        previous = "0"*64
        for event in self.history(cid):
            if event["previous_hash"] != previous or event["event_hash"] != self.event_digest(cid,event["time"],event["kind"],event["payload"],previous):
                raise PolicyError("Audit chain integrity failure")
            previous = event["event_hash"]
        return previous

    def list_campaigns(self, include_archived=False):
        with self.transaction() as db:
            return [dict(row) for row in db.execute("SELECT * FROM campaigns WHERE archived=0 OR ? ORDER BY id",(int(include_archived),))]

    def archive(self, cid):
        with self.transaction() as db:
            row=self.row(db,cid)
            if row["owner"]!=self.principal or State(row["state"]) not in TERMINAL:
                raise PolicyError("Only an owner may archive a terminal campaign")
            if not row["archived"]:
                db.execute("UPDATE campaigns SET archived=1,revision=revision+1 WHERE id=?",(cid,))
                self.event(db,cid,"archived",{"actor":self.principal})

    def history(self, cid):
        with self.transaction() as db:
            self.row(db, cid)
            return [dict(r) for r in db.execute("SELECT * FROM events WHERE campaign=? ORDER BY seq", (cid,))]

    def render(self, cid):
        row = self.get(cid)
        lines = ["# Campaign ledger", "", f"ID: {cid}", f"State: {row['state']}",
                 f"Revision: {row['revision']}", "", "## Objective", "", row['objective'], "", "## Events", ""]
        lines += [f"- {e['time']} {e['kind']}: {e['payload']}" for e in self.history(cid)]
        target = self.artifact(cid, "TASK_PLAN.md")
        temp = target.with_suffix(".tmp")
        temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temp.replace(target)
        return target
