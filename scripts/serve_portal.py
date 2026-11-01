"""Start the BTP-local portal; initial credentials are saved locally, never logged."""
import os
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
import json
import secrets
import sqlite3
import socket
import psutil
from pathlib import Path
import uvicorn
from pmda.portal import create_app

ROOT = Path(__file__).resolve().parents[1]
owner_path = ROOT / "runtime/portal/server-owner.json"
if owner_path.exists():
    previous = json.loads(owner_path.read_bytes())
    try:
        process = psutil.Process(previous["pid"])
        if abs(process.create_time() - previous["created"]) < .01:
            raise SystemExit("The previous portal process is still active or finishing preparation. Wait for it to exit before restarting.")
    except psutil.NoSuchProcess:
        pass
with socket.socket() as probe:
    if probe.connect_ex(("127.0.0.1", 8765)) == 0:
        raise SystemExit("Port 8765 is already in use. Open http://127.0.0.1:8765 or stop the existing portal before starting another instance.")
app = create_app()
with sqlite3.connect(app.state.data / "portal.sqlite3") as connection:
    empty = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
connection.close()
if empty:
    password = secrets.token_urlsafe(18)
    app.state.add_user("researcher", password, "admin", ["workspace", "stage7"])
    (app.state.data / "LOCAL_ACCESS.txt").write_text("Local PMDA portal\nURL: http://127.0.0.1:8765\nUsername: researcher\nPassword: " + password + "\n\nKeep this file private. It is ignored by Git. Accounts are stored as salted password hashes.\n", encoding="utf-8")
(ROOT / "web/openapi.json").write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
print("PMDA: http://127.0.0.1:8765 · credentials: runtime/portal/LOCAL_ACCESS.txt", flush=True)
if __name__ == "__main__":
    owner_path.write_text(json.dumps({"pid":os.getpid(),"created":psutil.Process().create_time()}),encoding="utf-8")
    try:
        uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning", access_log=False)
    finally:
        app.state.pool.shutdown(wait=True, cancel_futures=True)
        if owner_path.exists() and json.loads(owner_path.read_bytes()).get("pid")==os.getpid():
            owner_path.unlink()
