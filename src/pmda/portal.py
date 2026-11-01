"""Authenticated loopback research portal. No public deployment is implied."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import getpass
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import time
import uuid
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from .store import Store, digest
from .execution import ExecutionService
from .contracts import PolicyError
from . import portal_workflow as workflow

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "web"
LEAD = "CCOc1cc2ncnc(Nc3ccc(C)cc3)c2c2c1OCCO2"


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class NewCampaign(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str = Field(min_length=10, max_length=1000)
    lead: str = Field(default=LEAD, min_length=1, max_length=1000)
    candidates: int = Field(default=32, ge=4, le=112)
    seed: int = Field(default=42, ge=0, le=2147483647)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sha256: str = Field(pattern="^[0-9a-f]{64}$")
    revision: int = Field(ge=0)
    comments: str = Field(min_length=5, max_length=2000)
    confirmed: bool


class UserRequest(BaseModel):
    username: str = Field(pattern="^[A-Za-z0-9_-]{3,50}$")
    password: str = Field(min_length=12, max_length=200)
    role: str = Field(pattern="^(viewer|scientist|operator|admin)$")
    projects: list[str] = Field(default_factory=lambda: ["workspace"])


def create_app(directory=None, projects=None):
    data = Path(directory or ROOT / "runtime/portal").resolve()
    if not data.is_relative_to(ROOT):
        raise ValueError("Portal storage must remain in BTP")
    data.mkdir(parents=True, exist_ok=True)
    database = data / "portal.sqlite3"
    @contextmanager
    def db():
        connection = sqlite3.connect(database, timeout=20)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()
    with db() as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] > 1:
            raise ValueError("Portal database version is newer than this release")
        connection.executescript('''CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,salt TEXT,hash TEXT,role TEXT,projects TEXT);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,username TEXT,csrf TEXT,expires REAL);
        CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY,project TEXT,campaign TEXT,status TEXT,error TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS access_events(time REAL,username TEXT,action TEXT,project TEXT,campaign TEXT);
        PRAGMA user_version=1;''')
        connection.execute("UPDATE operations SET status='interrupted',error='Portal restarted. Inspect campaign state before resuming.' WHERE status IN ('queued','running')")
    project_map = projects or {"workspace": {"name": "BTP research workspace", "root": data / "campaigns", "readonly": False},
        "stage7": {"name": "Stage 7 reference campaign", "root": ROOT / "runtime/egfr-campaign-20261028T051715Z", "readonly": True}}
    for project in project_map.values():
        project["root"] = Path(project["root"]).resolve()
        if not project["root"].is_relative_to(ROOT):
            raise ValueError("Project escapes BTP")
    def add_user(username, password, role, scopes):
        if any(scope not in project_map for scope in scopes):
            raise ValueError("Unknown project membership")
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 310000).hex()
        with db() as connection:
            connection.execute("INSERT INTO users VALUES(?,?,?,?,?)", (username, salt, hashed, role, json.dumps(scopes)))
    app = FastAPI(title="PMDA Research API", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pmda-portal")
    app.state.add_user = add_user
    app.state.data = data
    app.state.pool = pool
    failures = {}

    @app.middleware("http")
    async def boundary(request, call_next):
        host = request.url.hostname
        if host not in {"127.0.0.1", "localhost", "testserver"}:
            return JSONResponse({"detail": "Untrusted host"}, status_code=400)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "Cross-origin request rejected"}, status_code=403)
            if int(request.headers.get("content-length", "0")) > 16384:
                return JSONResponse({"detail": "Request too large"}, status_code=413)
        response = await call_next(request)
        response.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store", "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response

    @app.exception_handler(PolicyError)
    async def policy_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(FileNotFoundError)
    async def missing_artifact(request, exc):
        return JSONResponse({"detail": "The requested artifact is not available yet."}, status_code=404)

    @app.exception_handler(ValueError)
    async def invalid_input(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    def authenticate(request: Request):
        token = request.cookies.get("pmda_session", "")
        with db() as connection:
            row = connection.execute("SELECT users.*,sessions.csrf,sessions.expires FROM sessions JOIN users USING(username) WHERE token=?", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not row or row["expires"] < time.time():
            raise HTTPException(401, "Sign in to the research workspace")
        user = dict(row)
        if request.method not in {"GET", "HEAD"} and not hmac.compare_digest(request.headers.get("x-csrf-token", ""), user["csrf"]):
            raise HTTPException(403, "Missing or invalid request token")
        return user

    def project_store(project, user, write=False, roles=()):
        if project not in project_map or project not in json.loads(user["projects"]):
            raise HTTPException(404, "Project not available")
        item = project_map[project]
        if write and (item["readonly"] or user["role"] not in {"admin", *roles}):
            raise HTTPException(403, "Role or project does not permit this action")
        return Store(item["root"], principal=getpass.getuser())

    def campaign_store(project, cid, user, write=False, roles=()):
        try:
            uuid.UUID(cid)
        except ValueError:
            raise HTTPException(404, "Campaign not found")
        store = project_store(project, user, write, roles)
        try:
            store.get(cid)
        except PolicyError:
            raise HTTPException(404, "Campaign not found")
        return store

    def access(user, action, project, cid):
        with db() as connection:
            connection.execute("INSERT INTO access_events VALUES(?,?,?,?,?)", (time.time(), user["username"], action, project, cid))

    def enqueue(project, cid, function, *args):
        operation = str(uuid.uuid4())
        with db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM operations WHERE project=? AND campaign=? AND status IN ('queued','running')", (project, cid)).fetchone():
                raise HTTPException(409, "A preparation operation is already queued")
            connection.execute("INSERT INTO operations VALUES(?,?,?,?,?,?)", (operation, project, cid, "queued", None, time.time()))
        def run():
            with db() as connection:
                connection.execute("UPDATE operations SET status='running' WHERE id=?", (operation,))
            try:
                function(*args)
                status, error = "succeeded", None
            except Exception as exc:
                status, error = "failed", str(exc)[:1500]
            with db() as connection:
                connection.execute("UPDATE operations SET status=?,error=? WHERE id=?", (status, error, operation))
        pool.submit(run)
        return operation

    @app.post("/api/v1/login")
    def login(body: Login, request: Request):
        key = request.client.host if request.client else "local"
        attempts = [t for t in failures.get(key, []) if t > time.time() - 60]
        if len(attempts) >= 10:
            raise HTTPException(429, "Too many attempts; wait one minute")
        with db() as connection:
            row = connection.execute("SELECT * FROM users WHERE username=?", (body.username,)).fetchone()
        salt = row["salt"] if row else "00" * 16
        actual = hashlib.pbkdf2_hmac("sha256", body.password.encode(), bytes.fromhex(salt), 310000).hex()
        if not row or not hmac.compare_digest(actual, row["hash"]):
            failures[key] = attempts + [time.time()]
            raise HTTPException(401, "Invalid credentials")
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with db() as connection:
            connection.execute("INSERT INTO sessions VALUES(?,?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), body.username, csrf, time.time() + 8 * 3600))
        response = JSONResponse({"username": body.username, "role": row["role"], "csrf": csrf})
        response.set_cookie("pmda_session", token, httponly=True, samesite="strict", max_age=8*3600)
        return response

    @app.post("/api/v1/logout")
    def logout(request: Request, user=Depends(authenticate)):
        with db() as connection:
            connection.execute("DELETE FROM sessions WHERE token=?", (hashlib.sha256(request.cookies.get("pmda_session", "").encode()).hexdigest(),))
        response = JSONResponse({"signed_out": True}); response.delete_cookie("pmda_session")
        return response

    @app.get("/api/v1/session")
    def session(user=Depends(authenticate)):
        return {k: user[k] for k in ("username", "role", "csrf")}

    @app.get("/api/v1/openapi.json")
    def specification(user=Depends(authenticate)):
        return app.openapi()

    @app.get("/api/v1/projects")
    def projects_list(user=Depends(authenticate)):
        return [{"id": key, "name": value["name"], "readonly": value["readonly"]} for key, value in project_map.items() if key in json.loads(user["projects"])]

    @app.get("/api/v1/registries")
    def registries(user=Depends(authenticate)):
        return {kind: [json.loads(p.read_bytes()) for p in (ROOT / "registries" / kind).glob("*.json")] for kind in ("targets", "datasets", "predictors", "components", "agents")}

    @app.get("/api/v1/benchmarks")
    def benchmarks(user=Depends(authenticate)):
        path = ROOT / "runtime/benchmark-stage8-20261028T052759Z"
        return {"protocol": json.loads((path / "protocol.json").read_bytes()), "results": json.loads((path / "results.json").read_bytes()),
            "decision": json.loads((path / "decision.json").read_bytes())}

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/orchestration")
    def orchestration(project: str, cid: str, user=Depends(authenticate)):
        store = campaign_store(project, cid, user)
        base = store.root / cid
        roles = []
        for role in ("planner", "formulator", "executor", "analyser"):
            folders = sorted([*base.glob("iteration-*/agents/" + role + "*"), *(base / "agents").glob(role + "*")], key=lambda p: p.stat().st_mtime)
            selected = folders[-1] if folders else None
            context = json.loads((selected / "context.json").read_bytes()) if selected and (selected / "context.json").exists() else None
            attempts = [json.loads(p.read_bytes()) for p in sorted(selected.glob("attempt-*.json"))] if selected else []
            roles.append({"role": role, "context": context, "attempts": attempts, "accepted": any(a.get("accepted") for a in attempts),
                "tokens": sum(a.get("usage", {}).get("total_tokens", 0) for a in attempts), "seconds": sum(a.get("seconds", 0) for a in attempts)})
        comparison = base / "iteration-comparison.json"
        return {"state": store.get(cid)["state"], "roles": roles, "comparison": json.loads(comparison.read_bytes()) if comparison.exists() else []}

    @app.get("/api/v1/health")
    def health(user=Depends(authenticate)):
        with db() as connection:
            operations = [dict(row) for row in connection.execute("SELECT * FROM operations ORDER BY created DESC LIMIT 50") if row["project"] in json.loads(user["projects"])]
        return {"mode": "local research alpha", "device": "CPU", "paid_services": False, "operations": operations,
                "limitations": ["No public deployment or clinical validation", "Agent output is constrained decision support"], "default_lead": LEAD}

    @app.post("/api/v1/users")
    def users(body: UserRequest, user=Depends(authenticate)):
        if user["role"] != "admin":
            raise HTTPException(403, "Administrator required")
        try:
            add_user(body.username, body.password, body.role, body.projects)
        except (ValueError, sqlite3.IntegrityError) as exc:
            raise HTTPException(409, str(exc))
        access(user, "create_user:" + body.username, "", "")
        return {"created": body.username}

    @app.get("/api/v1/projects/{project}/campaigns")
    def campaigns(project: str, user=Depends(authenticate)):
        return project_store(project, user).list_campaigns()

    @app.post("/api/v1/projects/{project}/campaigns", status_code=202)
    def create(project: str, body: NewCampaign, user=Depends(authenticate)):
        store = project_store(project, user, True, ("scientist",))
        cid = store.create(body.objective)
        workflow.save(store.root / cid / "request.json", body.model_dump())
        access(user, "create", project, cid)
        operation = enqueue(project, cid, workflow.prepare, store, cid, body.lead, body.candidates, body.seed)
        return {"id": cid, "operation": operation}

    @app.get("/api/v1/projects/{project}/campaigns/{cid}")
    def campaign(project: str, cid: str, user=Depends(authenticate)):
        store = campaign_store(project, cid, user)
        with store.transaction() as connection:
            jobs = [dict(row) for row in connection.execute("SELECT * FROM jobs WHERE campaign=? ORDER BY created", (cid,))]
            approvals = [dict(row) for row in connection.execute("SELECT id,kind,hash,actor,acting_role,time,comments FROM approvals WHERE campaign=? ORDER BY time", (cid,))]
        # Reconciliation reads worker-owned artifacts; it cannot launch a new process.
        for index, job in enumerate(jobs):
            if job["status"] in {"reserved", "starting", "running", "ambiguous"}:
                jobs[index] = ExecutionService(store).reconcile(job["id"])
        with db() as connection:
            operations = [dict(row) for row in connection.execute("SELECT * FROM operations WHERE project=? AND campaign=? ORDER BY created DESC", (project,cid))]
        return {"campaign": store.snapshot(cid), "jobs": jobs, "approvals": approvals, "operations": operations, "audit": store.history(cid)}

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/review")
    def review(project: str, cid: str, user=Depends(authenticate)):
        store = campaign_store(project, cid, user)
        names = {"AWAITING_PLAN_APPROVAL": "plan.json", "AWAITING_SCORE_APPROVAL": "score.json", "AWAITING_LAUNCH_APPROVAL": "config.toml"}
        row = store.get(cid)
        if row["state"] not in names:
            return {"available": False, "state": row["state"]}
        path = store.artifact(cid, names[row["state"]])
        return {"available": True, "artifact": path.name, "text": path.read_text(encoding="utf-8"), "sha256": digest(path.read_bytes()), "revision": row["revision"],
            "scope": "Research predictions only. Approval is bound to these exact bytes. Launch authorization is separate."}

    @app.post("/api/v1/projects/{project}/campaigns/{cid}/approve")
    def approve(project: str, cid: str, body: ApprovalRequest, user=Depends(authenticate)):
        store = campaign_store(project, cid, user, True, ("scientist", "operator"))
        current = review(project, cid, user)
        if not body.confirmed or not current["available"] or body.revision != current["revision"]:
            raise HTTPException(409, "Confirm the current review revision")
        launch = current["artifact"] == "config.toml"
        role = "operator" if launch else "scientist"
        if user["role"] not in {"admin", role}:
            raise HTTPException(403, "This approval requires role " + role)
        aid = store.approve(cid, current["artifact"], body.sha256, store.principal, role, f"Portal user {user['username']}: {body.comments}")
        access(user, "approve:" + current["artifact"], project, cid)
        return {"approval": aid, "state": store.get(cid)["state"]}

    @app.post("/api/v1/projects/{project}/campaigns/{cid}/advance", status_code=202)
    def advance(project: str, cid: str, user=Depends(authenticate)):
        store = campaign_store(project, cid, user, True, ("scientist", "operator"))
        if store.get(cid)["state"] not in {"FORMULATING", "CONFIGURING", "EVALUATING"}:
            raise HTTPException(409, "No preparation step available")
        access(user, "prepare_next_step", project, cid)
        return {"operation": enqueue(project, cid, workflow.advance, store, cid)}

    @app.post("/api/v1/projects/{project}/campaigns/{cid}/resume", status_code=202)
    def resume(project: str, cid: str, user=Depends(authenticate)):
        store = campaign_store(project, cid, user, True, ("scientist",))
        if store.get(cid)["state"] not in {"DRAFT", "PLANNING"}:
            raise HTTPException(409, "Use the next review action; engine jobs are never automatically restarted")
        request = NewCampaign.model_validate_json((store.root / cid / "request.json").read_bytes())
        access(user, "resume_preparation", project, cid)
        return {"operation": enqueue(project, cid, workflow.prepare, store, cid, request.lead, request.candidates, request.seed)}

    @app.post("/api/v1/projects/{project}/campaigns/{cid}/launch", status_code=202)
    def launch(project: str, cid: str, user=Depends(authenticate)):
        store = campaign_store(project, cid, user, True, ("operator",))
        with store.transaction() as connection:
            row = connection.execute("SELECT id FROM approvals WHERE campaign=? AND kind='launch' ORDER BY time DESC LIMIT 1", (cid,)).fetchone()
        if not row:
            raise HTTPException(409, "Launch approval required")
        result = ExecutionService(store).launch(cid, row[0])
        access(user, "launch", project, cid)
        return result

    @app.post("/api/v1/projects/{project}/campaigns/{cid}/cancel")
    def cancel(project: str, cid: str, user=Depends(authenticate)):
        store = campaign_store(project, cid, user, True, ("operator",))
        with store.transaction() as connection:
            row = connection.execute("SELECT id FROM jobs WHERE campaign=? AND status IN ('reserved','starting','running') ORDER BY created DESC LIMIT 1", (cid,)).fetchone()
        if not row:
            raise HTTPException(409, "No active job to cancel")
        access(user, "cancel", project, cid)
        return ExecutionService(store).cancel(row[0])

    def evaluation_files(store, cid):
        base = store.root / cid
        files = sorted(base.glob("iteration-*/evaluation/evaluation.json"))
        if (base / "evaluation/evaluation.json").exists():
            files.append(base / "evaluation/evaluation.json")
        return files

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/candidates")
    def candidates(project: str, cid: str, offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                   q: str = Query("", max_length=200), passed: bool | None = None, iteration: int = Query(-1, ge=-1, le=10), user=Depends(authenticate)):
        store = campaign_store(project, cid, user)
        files = evaluation_files(store, cid)
        if not files:
            return {"rows": [], "total": 0, "iterations": 0}
        if iteration >= len(files):
            raise HTTPException(404, "Iteration unavailable")
        result = json.loads(files[iteration].read_bytes())
        rows = [row for row in result["rows"] if (passed is None or bool(row.get("passes_configured_gates")) == passed) and q.lower() in json.dumps(row).lower()]
        return {"rows": rows[offset:offset+limit], "total": len(rows), "iterations": len(files), "summary": result["summary"]}

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/portfolio")
    def final_portfolio(project: str, cid: str, user=Depends(authenticate)):
        path = campaign_store(project, cid, user).root / cid / "final-portfolio.json"
        return {"available": path.exists(), "rows": json.loads(path.read_bytes()) if path.exists() else []}

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/space")
    def space(project: str, cid: str, user=Depends(authenticate)):
        files = evaluation_files(campaign_store(project, cid, user), cid)
        rows = json.loads(files[-1].read_bytes())["rows"] if files else []
        from collections import Counter
        return {"axes": ["logP", "molecular weight"], "scope": "Descriptor space, first 1000 valid rows; not a potency map",
            "points": [{"x": r["descriptors"]["logp"], "y": r["descriptors"]["mw"], "row": r["row"], "passed": r.get("passes_configured_gates", False)} for r in rows if r["valid"]][:1000],
            "scaffolds": Counter(r["scaffold"] for r in rows if r["valid"]).most_common(12)}

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/molecule/{index}")
    def molecule(project: str, cid: str, index: int, user=Depends(authenticate)):
        files = evaluation_files(campaign_store(project, cid, user), cid)
        rows = json.loads(files[-1].read_bytes())["rows"] if files else []
        if index < 0 or index >= len(rows) or not rows[index]["valid"]:
            raise HTTPException(404, "Structure unavailable")
        from rdkit import Chem
        from rdkit.Chem.Draw import rdMolDraw2D
        drawer = rdMolDraw2D.MolDraw2DSVG(440, 250)
        drawer.DrawMolecule(Chem.MolFromSmiles(rows[index]["canonical_smiles"]))
        drawer.FinishDrawing()
        return Response(drawer.GetDrawingText(), media_type="image/svg+xml")

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/files")
    def files(project: str, cid: str, user=Depends(authenticate)):
        base = campaign_store(project, cid, user).root / cid
        allowed = {".json", ".toml", ".md", ".csv", ".parquet", ".log"}
        return [{"path": str(p.relative_to(base)).replace("\\", "/"), "bytes": p.stat().st_size} for p in base.rglob("*") if p.is_file() and p.suffix in allowed and p.stat().st_size <= 16 * 1024 * 1024]

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/download")
    def download(project: str, cid: str, path: str = Query(max_length=400), user=Depends(authenticate)):
        store = campaign_store(project, cid, user)
        allowed = {row["path"] for row in files(project, cid, user)}
        if path not in allowed:
            raise HTTPException(404, "Artifact unavailable")
        item = store.artifact(cid, path)
        access(user, "download:" + path, project, cid)
        return FileResponse(item, filename=item.name, media_type="application/octet-stream")

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/logs")
    def logs(project: str, cid: str, user=Depends(authenticate)):
        base = campaign_store(project, cid, user).root / cid
        logs = sorted((base / "jobs").glob("*/engine.log"), key=lambda p: p.stat().st_mtime)
        if not logs:
            return {"text": "No engine log yet."}
        with logs[-1].open("rb") as stream:
            stream.seek(max(0, logs[-1].stat().st_size - 16000))
            return {"text": stream.read().decode("utf-8", errors="replace")}

    @app.get("/api/v1/projects/{project}/campaigns/{cid}/events")
    async def events(project: str, cid: str, user=Depends(authenticate)):
        store = campaign_store(project, cid, user)
        async def stream():
            last = None
            for _ in range(30):
                row = await asyncio.to_thread(store.get, cid)
                payload = json.dumps({"state": row["state"], "revision": row["revision"]})
                if payload != last:
                    yield "data: " + payload + "\n\n"
                    last = payload
                else:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(2)
        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
