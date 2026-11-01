"""Lifecycle for one BTP-local CPU model server; no global service changes."""
from contextlib import contextmanager
import json
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import time
import requests

ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def local_server(log_directory):
    executables = list((ROOT / "vendor/llama.cpp/bin").rglob("llama-server.exe"))
    model = ROOT / "models/agents/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    if len(executables) != 1 or not model.is_file():
        raise RuntimeError("Run scripts/setup_agent_runtime.py first")
    provenance = json.loads((ROOT / "models/agents/provenance.json").read_bytes())
    for entry in provenance["assets"]:
        asset = (ROOT / entry["path"]).resolve()
        if not asset.is_relative_to(ROOT):
            raise ValueError("Inference asset escapes BTP")
        with asset.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != entry["sha256"]:
            raise ValueError("Inference asset checksum mismatch")
    # Ask the OS for an unused loopback port, then pass it to our own process.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    directory = Path(log_directory)
    directory.mkdir(parents=True, exist_ok=True)
    command = [str(executables[0]), "-m", str(model), "--host", "127.0.0.1", "--port", str(port),
               "-c", "4096", "-t", "4", "-ngl", "0", "--parallel", "1", "--alias", "pmda-local"]
    (directory / "server-command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
    with (directory / "server.log").open("wb") as log:
        process = subprocess.Popen(command, cwd=directory, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            url = f"http://127.0.0.1:{port}"
            with requests.Session() as session:
                session.trust_env = False
                for _ in range(120):
                    if process.poll() is not None:
                        raise RuntimeError("Local inference server exited; inspect server.log")
                    try:
                        if session.get(url + "/health", timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                    time.sleep(.5)
                else:
                    raise RuntimeError("Local inference startup timed out")
            yield url
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
